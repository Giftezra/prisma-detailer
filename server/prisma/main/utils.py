from django.conf import settings

def get_full_media_url(relative_url):
    """
    Convert a relative media URL to a full URL.
    
    Args:
        relative_url (str): Relative URL like '/media/products/images/...'
        
    Returns:
        str: Full URL with the server base URL
    """
    if not relative_url:
        return None
    
    # Get the base URL from settings or use a default
    # You can set this in your Django settings
    base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    
    # Remove leading slash if present to avoid double slashes
    if relative_url.startswith('/'):
        relative_url = relative_url[1:]
    
    # Combine base URL with relative URL
    return f"{base_url}/{relative_url}" 