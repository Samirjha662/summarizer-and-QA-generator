import io

def create_download_link(data, filename):
    """
    Creates a download link for the given data.
    Streamlit handles this natively with st.download_button, 
    but we might need to format the data first.
    """
    if isinstance(data, str):
        return data.encode('utf-8')
    return data
