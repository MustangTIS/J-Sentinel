
Set ws = CreateObject("WScript.Shell")
Set lnk = ws.CreateShortcut("C:\Users\Mustang_TIS\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\J-Sentinel_CallBack.lnk")
lnk.TargetPath = "C:\Users\Mustang_TIS\AppData\Local\Programs\Python\Python314\pythonw.exe"
lnk.Arguments = ""C:\j-sent\bot.py""
lnk.WorkingDirectory = "C:\j-sent"
lnk.IconLocation = "C:\Users\Mustang_TIS\AppData\Local\Programs\Python\Python314\pythonw.exe"
lnk.Save
