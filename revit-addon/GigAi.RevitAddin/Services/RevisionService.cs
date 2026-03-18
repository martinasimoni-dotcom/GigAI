using Autodesk.Revit.DB;

namespace GigAi.RevitAddin.Services
{
    internal sealed class RevisionService
    {
        public Revision CreateRevision(Document document, string description, bool issued)
        {
            Revision revision = Revision.Create(document);
            revision.Description = description;
            revision.Issued = issued;
            return revision;
        }
    }
}