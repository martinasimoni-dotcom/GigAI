using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using GigAi.RevitAddin.Services;
using GigAi.RevitAddin.Utils;

namespace GigAi.RevitAddin.Commands
{
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public sealed class CreateRevisionCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            int queued = GigAiSyncRuntime.TriggerManualSync();
            Logger.Info($"Manual GigAI sync triggered. Files queued: {queued}.");

            TaskDialog.Show(
                "GigAI Sync",
                queued > 0
                    ? $"Queued {queued} request file(s) for processing."
                    : "No pending request files found in the GigAI inbox.");

            return Result.Succeeded;
        }
    }
}