using System;
using System.Reflection;
using Autodesk.Revit.UI;
using GigAi.RevitAddin.Services;

namespace GigAi.RevitAddin
{
    public class App : IExternalApplication
    {
        private const string TabName = "GigAI";
        private const string PanelName = "Assistant";

        public Result OnStartup(UIControlledApplication application)
        {
            try
            {
                application.CreateRibbonTab(TabName);
            }
            catch (Exception)
            {
                // Tab may already exist.
            }

            RibbonPanel panel = application.CreateRibbonPanel(TabName, PanelName);
            string assemblyPath = Assembly.GetExecutingAssembly().Location;

            PushButtonData buttonData = new PushButtonData(
                "GigAiVoiceFocus",
                "Voice Focus",
                assemblyPath,
                "GigAi.RevitAddin.FocusVoiceCommand"
            )
            {
                ToolTip = "Send transcript to GigAI API and focus the matched room/space."
            };

            panel.AddItem(buttonData);

            PushButtonData syncButtonData = new PushButtonData(
                "GigAiRevisionSync",
                "GigAI Sync",
                assemblyPath,
                "GigAi.RevitAddin.Commands.CreateRevisionCommand"
            )
            {
                ToolTip = "Manually process pending GigAI revision events from the local inbox."
            };

            panel.AddItem(syncButtonData);

            PushButtonData accSyncButtonData = new PushButtonData(
                "GigAiAccReadonlySync",
                "Sync ACC Issues",
                assemblyPath,
                "GigAi.RevitAddin.Commands.SyncAccIssuesCommand"
            )
            {
                ToolTip = "Read the latest local ACC snapshot and place or update readonly issue bubbles in Revit."
            };

            panel.AddItem(accSyncButtonData);

            GigAiSyncRuntime.Initialize();
            return Result.Succeeded;
        }

        public Result OnShutdown(UIControlledApplication application)
        {
            GigAiSyncRuntime.Shutdown();
            return Result.Succeeded;
        }
    }
}
