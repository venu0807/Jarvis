param(
    [Parameter(Mandatory=$true)]
    [string]$Title,
    
    [Parameter(Mandatory=$true)]
    [string]$Message
)

[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$TextNodes = $Template.GetElementsByTagName("text")
$TextNodes.Item(0).AppendChild($Template.CreateTextNode($Title)) | Out-Null
$TextNodes.Item(1).AppendChild($Template.CreateTextNode($Message)) | Out-Null

$Toast = [Windows.UI.Notifications.ToastNotification]::new($Template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Jarvis Automation").Show($Toast)
