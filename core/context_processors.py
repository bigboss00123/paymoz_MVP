from .models import ContactoSuporte

def support_contacts(request):
    """
    Makes the support contact information available in all templates.
    """
    contacts = ContactoSuporte.load()
    return {'support_contacts': contacts}
