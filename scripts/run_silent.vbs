Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strRootDir = FSO.GetParentFolderName(strScriptDir)
WshShell.CurrentDirectory = strRootDir
WshShell.Run "pythonw app.py", 0, False
