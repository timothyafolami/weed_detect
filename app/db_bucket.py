from datetime import datetime
from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


# authentication set up
user_email:str  = os.environ.get("USER_EMAIL_1")
user_password: str = os.environ.get("USER_PASSWORD_1")

# Sign in the user
auth_response = supabase.auth.sign_in_with_password({"email": user_email, "password": user_password})

# checking if a file exists
def file_exists(file_path):
    return os.path.isfile(file_path)

# adding detected weed shp files to the bucket
def upload_file_to_bucket(file_path: str, storage_path: str = "shapefiles_storage/", bucket_name: str = "shapefiles-bucket") -> None:
    # firstlt checking if the path exists 
    if not file_exists(file_path):
        print(f"Error: {file_path} does not exist")
        return None
    # extracting the file ame 
    file_name = os.path.basename(file_path) 
    
    # adding today's date and time to the file name
    file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_") + file_name
    
    with open(file_path, 'rb') as file:
        response = supabase.storage.from_(bucket_name).upload(storage_path+file_name, file)

    if response.status_code != 200:
        return f"Error: {response.json()['message']}"
    else:
        return "File uploaded successfully:", response.json()
        
if __name__ == "__main__":
    # Define the relative path to the file from the current script location
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'db setup.zip'))
    
    # upload the file to the bucket
    response = upload_file_to_bucket(file_path=file_path)
    print(response)