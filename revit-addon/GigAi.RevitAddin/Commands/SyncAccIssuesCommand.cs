using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using GigAi.RevitAddin.Services;

namespace GigAi.RevitAddin.Commands
{
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public sealed class SyncAccIssuesCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                var service = new AccAnnotationService();
                AccAnnotationSyncSummary summary = service.Run(commandData.Application);

                TaskDialog.Show(
                    "Sync ACC Issues",
                    $"Created: {summary.Created}\n" +
                    $"Updated: {summary.Updated}\n" +
                    $"Removed: {summary.Removed}\n" +
                    $"Unchanged: {summary.Unchanged}\n" +
                    $"Failed: {summary.Failed}");

                return summary.Failed > 0 ? Result.Failed : Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = $"Error: {ex.Message}\n{ex.StackTrace}";
                return Result.Failed;
            }
        }
    }
}
