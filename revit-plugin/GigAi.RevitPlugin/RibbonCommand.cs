using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using System;
using System.Windows.Forms;

namespace GigAi.RevitPlugin
{
    /// <summary>
    /// Revit external application — creates the GigAI ribbon tab on startup.
    /// </summary>
    [Transaction(TransactionMode.ReadOnly)]
    public class GigAiApp : IExternalApplication
    {
        public Result OnStartup(UIControlledApplication app)
        {
            try
            {
                app.CreateRibbonTab("GigAI");
                RibbonPanel panel = app.CreateRibbonPanel("GigAI", "RFI Tools");

                string assemblyPath = typeof(GigAiApp).Assembly.Location;

                PushButtonData buttonData = new PushButtonData(
                    "LocateRFI",
                    "Locate RFI",
                    assemblyPath,
                    typeof(LocateRfiCommand).FullName)
                {
                    ToolTip = "Find an RFI proposal in the GigAI backend and display its details."
                };

                panel.AddItem(buttonData);
                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("GigAI — Startup Error", ex.Message);
                return Result.Failed;
            }
        }

        public Result OnShutdown(UIControlledApplication app) => Result.Succeeded;
    }

    /// <summary>
    /// External command bound to the "Locate RFI" button.
    /// Opens the search dialog.
    /// </summary>
    [Transaction(TransactionMode.ReadOnly)]
    public class LocateRfiCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                var dialog = new LocateRfiDialog();
                dialog.ShowDialog();
                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
}
