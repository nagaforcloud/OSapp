'==============================================================================
' Onestream Data Load Business Rule - Sample VBScript
'==============================================================================
'
' Purpose: Validate and transform data during load process
' Context: Data Management workspace
' Author: Generated for demonstration
' Date: September 2025
'
' This business rule performs the following functions:
' 1. Validates data format and structure
' 2. Transforms data as needed
' 3. Applies business logic validation
' 4. Logs errors for troubleshooting
'
'==============================================================================

Function ValidateAndTransformData(strData, strEntity, strAccount, strTime)
    ' Initialize return value
    ValidateAndTransformData = True
    
    ' Get the API object
    Dim api
    Set api = BWX_Api
    
    ' Get the data context
    Dim dataContext
    Set dataContext = api.Data 
    
    ' Get the error log
    Dim errorLog
    Set errorLog = api.ErrorLog
    
    ' Validation and transformation logic
    On Error Resume Next
    
    ' 1. Validate Entity exists in hierarchy
    If Not IsValidEntity(strEntity) Then
        errorLog.Add "Invalid Entity Code", "Entity " & strEntity & " not found in hierarchy"
        ValidateAndTransformData = False
        Exit Function
    End If
    
    ' 2. Validate Account exists and is loadable
    If Not IsValidAccount(strAccount) Then
        errorLog.Add "Invalid Account Code", "Account " & strAccount & " not found or not loadable"
        ValidateAndTransformData = False
        Exit Function
    End If
    
    ' 3. Validate Time dimension format
    If Not IsValidTimeFormat(strTime) Then
        errorLog.Add "Invalid Time Format", "Time period " & strTime & " is not in valid YYYYMM format"
        ValidateAndTransformData = False
        Exit Function
    End If
    
    ' 4. Validate data is numeric
    If Not IsNumeric(strData) Then
        ' Attempt to clean the data
        Dim cleanedData
        cleanedData = CleanNumericData(strData)
        If IsNumeric(cleanedData) Then
            ' Update the data with cleaned value
            strData = cleanedData
            dataContext.Value = CDbl(strData)
        Else
            errorLog.Add "Invalid Data Format", "Data value '" & strData & "' is not numeric and cannot be converted"
            ValidateAndTransformData = False
            Exit Function
        End If
    Else
        ' Ensure data is properly typed as double
        dataContext.Value = CDbl(strData)
    End If
    
    ' 5. Apply business rules for specific accounts
    If ApplyAccountBusinessRules(strAccount, strData, strEntity, strTime) = False Then
        ValidateAndTransformData = False
        Exit Function
    End If
    
    ' 6. Check for negative values where not allowed
    If IsNegativeNotAllowed(strAccount) And CDbl(strData) < 0 Then
        errorLog.Add "Negative Value Not Allowed", "Account " & strAccount & " does not accept negative values"
        ValidateAndTransformData = False
        Exit Function
    End If
    
    ' If we get here, all validations passed
    ValidateAndTransformData = True
    
    ' Clean up
    Set api = Nothing
    Set dataContext = Nothing
    Set errorLog = Nothing
End Function

Function IsValidEntity(strEntity)
    ' Check if entity exists in the dimension
    Dim api
    Set api = BWX_Api
    
    ' This is a simplified check - in real implementation, 
    ' you would check against the actual entity dimension
    IsValidEntity = (Len(Trim(strEntity)) > 0) And (InStr(strEntity, " ") = 0)
    
    Set api = Nothing
End Function

Function IsValidAccount(strAccount)
    ' Check if account exists and is loadable
    Dim api
    Set api = BWX_Api
    
    ' This is a simplified check - in real implementation,
    %REM
    ' you would check:
    ' 1. Account exists in dimension
    ' 2. Account is not a calculated member
    ' 3. Account is enabled for data loading
    %END REM
    
    IsValidAccount = (Len(Trim(strAccount)) > 0)
    
    Set api = Nothing
End Function

Function IsValidTimeFormat(strTime)
    ' Validate YYYYMM format
    If Len(strTime) <> 6 Then
        IsValidTimeFormat = False
        Exit Function
    End If
    
    ' Check if all characters are numeric
    Dim i
    For i = 1 To 6
        If Not IsNumeric(Mid(strTime, i, 1)) Then
            IsValidTimeFormat = False
            Exit Function
        End If
    Next
    
    ' Check year and month ranges
    Dim yearPart, monthPart
    yearPart = CInt(Left(strTime, 4))
    monthPart = CInt(Right(strTime, 2))
    
    IsValidTimeFormat = (yearPart >= 1900 And yearPart <= 2100) And (monthPart >= 1 And monthPart <= 12)
End Function

Function CleanNumericData(strData)
    ' Remove common non-numeric characters but preserve negative sign and decimal
    Dim cleaned
    cleaned = strData
    
    ' Remove currency symbols, commas, spaces
    cleaned = Replace(cleaned, "$", "")
    cleaned = Replace(cleaned, "€", "")
    cleaned = Replace(cleaned, "£", "")
    cleaned = Replace(cleaned, ",", "")
    cleaned = Replace(cleaned, " ", "")
    
    ' Handle parentheses for negative numbers
    If Left(cleaned, 1) = "(" And Right(cleaned, 1) = ")" Then
        cleaned = "-" & Mid(cleaned, 2, Len(cleaned) - 2)
    End If
    
    CleanNumericData = cleaned
End Function

Function ApplyAccountBusinessRules(strAccount, strData, strEntity, strTime)
    ' Apply specific business rules based on account type
    ApplyAccountBusinessRules = True
    
    Dim api, errorLog
    Set api = BWX_Api
    Set errorLog = api.ErrorLog
    
    ' Example: Revenue accounts should not have negative values in most cases
    If InStr(UCase(strAccount), "REVENUE") > 0 Or InStr(UCase(strAccount), "SALES") > 0 Then
        If CDbl(strData) < 0 Then
            ' Log a warning but allow the data
            errorLog.Add "Warning - Negative Revenue", "Revenue account " & strAccount & " has negative value. Please verify."
        End If
    End If
    
    ' Example: Balance sheet accounts validation
    If InStr(UCase(strAccount), "ASSET") > 0 Or InStr(UCase(strAccount), "LIABILITY") > 0 Then
        ' Could add balance sheet specific validations here
    End If
    
    Set api = Nothing
    Set errorLog = Nothing
End Function

Function IsNegativeNotAllowed(strAccount)
    ' Define accounts that should not have negative values
    Dim restrictedAccounts
    restrictedAccounts = Array("CASH", "RECEIVABLES", "INVENTORY", "PREPAID_EXPENSES")
    
    Dim i
    For i = 0 To UBound(restrictedAccounts)
        If UCase(strAccount) = UCase(restrictedAccounts(i)) Then
            IsNegativeNotAllowed = True
            Exit Function
        End If
    Next
    
    IsNegativeNotAllowed = False
End Function

'==============================================================================
' Main Business Rule Execution
'==============================================================================

Sub BWX_Run()
    ' Main execution point for the business rule
    Dim api, dataContext
    Set api = BWX_Api
    Set dataContext = api.Data
    
    ' Get current data values
    Dim currentValue, currentEntity, currentAccount, currentTime
    currentValue = dataContext.Value
    currentEntity = dataContext.GetDimValue("Entity")
    currentAccount = dataContext.GetDimValue("Account")
    currentTime = dataContext.GetDimValue("Time")
    
    ' Validate and transform the data
    If Not ValidateAndTransformData(CStr(currentValue), currentEntity, currentAccount, currentTime) Then
        ' Validation failed - data will be rejected
        ' Error already logged in the function
        dataContext.RejectData = True
    End If
    
    ' Clean up
    Set api = Nothing
    Set dataContext = Nothing
End Sub

'==============================================================================
' Helper function for logging
'==============================================================================

Sub LogMessage(strLevel, strMessage)
    Dim api, log
    Set api = BWX_Api
    Set log = api.Log
    
    Select Case UCase(strLevel)
        Case "INFO"
            log.Info strMessage
        Case "WARN"
            log.Warn strMessage
        Case "ERROR"
            log.Error strMessage
        Case Else
            log.Info strMessage
    End Select
    
    Set api = Nothing
    Set log = Nothing
End Sub