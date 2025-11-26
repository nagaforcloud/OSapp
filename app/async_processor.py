# app/async_processor.py
"""
Async processing utilities for the Onestream RAG application.
Provides async document processing, batch operations, and concurrent execution.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable, Union
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps, partial
import threading
from dataclasses import dataclass

from app.enhanced_logger import get_current_context, info, debug, warning, error, logged_operation


@dataclass
class ProcessingResult:
    """Result of async processing operation."""
    success: bool
    data: Any
    error: Optional[str] = None
    duration_ms: float = 0
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = None


class AsyncProcessor:
    """Advanced async processing with resource management."""

    def __init__(self, max_workers: int = 4, max_processes: int = 2):
        """
        Initialize async processor.

        Args:
            max_workers: Maximum number of thread workers
            max_processes: Maximum number of process workers
        """
        self.max_workers = max_workers
        self.max_processes = max_processes
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=max_processes)
        self.active_tasks = set()
        self.lock = threading.Lock()

    async def run_in_thread(self, func: Callable, *args, **kwargs) -> ProcessingResult:
        """Run function in thread pool."""
        start_time = time.time()
        worker_id = f"thread-{threading.current_thread().ident}"
        context = get_current_context()

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_executor,
                partial(func, *args, **kwargs)
            )
            duration_ms = (time.time() - start_time) * 1000

            debug("Thread execution completed",
                  worker_id=worker_id,
                  duration_ms=duration_ms,
                  **context)

            return ProcessingResult(
                success=True,
                data=result,
                duration_ms=duration_ms,
                worker_id=worker_id,
                metadata={'execution_type': 'thread'}
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error("Thread execution failed",
                  worker_id=worker_id,
                  error=str(e),
                  duration_ms=duration_ms,
                  **context)

            return ProcessingResult(
                success=False,
                data=None,
                error=str(e),
                duration_ms=duration_ms,
                worker_id=worker_id,
                metadata={'execution_type': 'thread'}
            )

    async def run_in_process(self, func: Callable, *args, **kwargs) -> ProcessingResult:
        """Run CPU-intensive function in process pool."""
        start_time = time.time()
        worker_id = f"process-{os.getpid()}"
        context = get_current_context()

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.process_executor,
                partial(func, *args, **kwargs)
            )
            duration_ms = (time.time() - start_time) * 1000

            debug("Process execution completed",
                  worker_id=worker_id,
                  duration_ms=duration_ms,
                  **context)

            return ProcessingResult(
                success=True,
                data=result,
                duration_ms=duration_ms,
                worker_id=worker_id,
                metadata={'execution_type': 'process'}
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error("Process execution failed",
                  worker_id=worker_id,
                  error=str(e),
                  duration_ms=duration_ms,
                  **context)

            return ProcessingResult(
                success=False,
                data=None,
                error=str(e),
                duration_ms=duration_ms,
                worker_id=worker_id,
                metadata={'execution_type': 'process'}
            )

    async def batch_process(self, items: List[Any], processor_func: Callable,
                           batch_size: int = 10, use_processes: bool = False) -> List[ProcessingResult]:
        """
        Process items in batches concurrently.

        Args:
            items: Items to process
            processor_func: Function to process each item
            batch_size: Number of items per batch
            use_processes: Whether to use process pool for CPU-intensive tasks

        Returns:
            List of processing results
        """
        context = get_current_context()
        info(f"Starting batch processing of {len(items)} items",
              batch_size=batch_size,
              use_processes=use_processes,
              **context)

        # Create batches
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

        # Process batches concurrently
        tasks = []
        for i, batch in enumerate(batches):
            task = self._process_batch(batch, processor_func, i, use_processes)
            tasks.append(task)

        # Wait for all batches to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        all_results = []
        for result in results:
            if isinstance(result, Exception):
                error(f"Batch processing error: {result}", **context)
                all_results.append(ProcessingResult(
                    success=False,
                    data=None,
                    error=str(result),
                    metadata={'execution_type': 'batch_error'}
                ))
            else:
                all_results.extend(result)

        successful_results = [r for r in all_results if r.success]
        failed_results = [r for r in all_results if not r.success]

        info(f"Batch processing completed",
              total=len(all_results),
              successful=len(successful_results),
              failed=len(failed_results),
              **context)

        return all_results

    async def _process_batch(self, batch: List[Any], processor_func: Callable,
                            batch_id: int, use_processes: bool) -> List[ProcessingResult]:
        """Process a single batch."""
        context = get_current_context()
        tasks = []

        for item in batch:
            if use_processes:
                task = self.run_in_process(processor_func, item)
            else:
                task = self.run_in_thread(processor_func, item)
            tasks.append(task)

        batch_results = await asyncio.gather(*tasks)
        debug(f"Batch {batch_id} processed",
              items=len(batch),
              successful=len([r for r in batch_results if r.success]),
              **context)

        return batch_results

    async def parallel_map(self, func: Callable, items: List[Any],
                          max_concurrency: int = None) -> List[ProcessingResult]:
        """
        Apply function to items with controlled concurrency.

        Args:
            func: Function to apply
            items: Items to process
            max_concurrency: Maximum concurrent tasks

        Returns:
            List of processing results
        """
        max_concurrency = max_concurrency or self.max_workers
        context = get_current_context()

        info(f"Starting parallel map of {len(items)} items",
              max_concurrency=max_concurrency,
              **context)

        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_with_semaphore(item):
            async with semaphore:
                return await self.run_in_thread(func, item)

        tasks = [process_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks)

        return results

    async def gather_with_timeout(self, *tasks, timeout: float = None):
        """
        Gather tasks with timeout.

        Args:
            *tasks: Tasks to gather
            timeout: Timeout in seconds

        Returns:
            List of results, with timed-out tasks marked as failed
        """
        context = get_current_context()

        try:
            return await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
        except asyncio.TimeoutError:
            warning(f"Tasks timed out after {timeout} seconds", **context)
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            return [ProcessingResult(
                success=False,
                data=None,
                error="Task timed out",
                metadata={'timeout': timeout}
            ) for _ in tasks]

    def shutdown(self, wait: bool = True):
        """Shutdown executors."""
        info("Shutting down async processor")
        self.thread_executor.shutdown(wait=wait)
        self.process_executor.shutdown(wait=wait)


# Global async processor instance
async_processor = AsyncProcessor()


def async_task(max_workers: int = None, use_processes: bool = False):
    """
    Decorator for making functions async-executable.

    Args:
        max_workers: Maximum number of concurrent workers
        use_processes: Whether to use process pool
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if use_processes:
                return await async_processor.run_in_process(func, *args, **kwargs)
            else:
                return await async_processor.run_in_thread(func, *args, **kwargs)

        return async_wrapper

    def sync_wrapper(*args, **kwargs):
        """Synchronous wrapper that runs in thread pool."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if use_processes:
                task = async_processor.run_in_process(func, *args, **kwargs)
            else:
                task = async_processor.run_in_thread(func, *args, **kwargs)
            return loop.run_until_complete(task)
        finally:
            loop.close()

        # Add async execution capability
        sync_wrapper.async_execute = async_wrapper
        sync_wrapper.__async_enabled__ = True

        return sync_wrapper

    return decorator


async def async_batch_operation(operation_func: Callable, items: List[Any],
                              batch_size: int = 10, **kwargs) -> List[ProcessingResult]:
    """
    Convenience function for batch operations.

    Args:
        operation_func: Function to execute on each item
        items: Items to process
        batch_size: Size of each batch
        **kwargs: Additional arguments for batch processing

    Returns:
        List of processing results
    """
    return await async_processor.batch_process(
        items=items,
        processor_func=operation_func,
        batch_size=batch_size,
        **kwargs
    )


class DocumentProcessor:
    """Specialized async document processor."""

    def __init__(self):
        self.processing_stats = {
            'documents_processed': 0,
            'total_processing_time': 0,
            'errors': 0
        }

    @logged_operation("document_processing_batch")
    async def process_documents(self, documents: List[Any],
                              chunk_size: int = 50) -> List[ProcessingResult]:
        """
        Process documents asynchronously in batches.

        Args:
            documents: List of documents to process
            chunk_size: Number of documents per batch

        Returns:
            List of processing results
        """
        context = get_current_context()
        start_time = time.time()

        # Document processing function
        def process_single_document(document):
            """Process a single document."""
            # This would be your actual document processing logic
            time.sleep(0.1)  # Simulate processing time
            return {
                'id': getattr(document, 'id', 'unknown'),
                'content': getattr(document, 'content', ''),
                'processed': True,
                'timestamp': time.time()
            }

        results = await async_processor.batch_process(
            items=documents,
            processor_func=process_single_document,
            batch_size=chunk_size
        )

        # Update statistics
        processing_time = time.time() - start_time
        self.processing_stats['documents_processed'] += len(documents)
        self.processing_stats['total_processing_time'] += processing_time
        self.processing_stats['errors'] += len([r for r in results if not r.success])

        info("Document batch processing completed",
              documents_count=len(documents),
              processing_time=processing_time,
              success_rate=len([r for r in results if r.success]) / len(results) * 100,
              **context)

        return results

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        total_time = self.processing_stats['total_processing_time']
        docs_processed = self.processing_stats['documents_processed']
        avg_time = total_time / docs_processed if docs_processed > 0 else 0

        return {
            **self.processing_stats,
            'average_processing_time': avg_time,
            'documents_per_second': docs_processed / total_time if total_time > 0 else 0
        }


# Global document processor
document_processor = DocumentProcessor()