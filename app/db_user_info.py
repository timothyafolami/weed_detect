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


# creating a function to insert user info
def insert_user_info(user_info: dict) -> None:  
    try:
        response = supabase.table("user-info").insert(user_info).execute()
        return f"'response': {response}"
    except Exception as e:
        print(e)
        
        
if __name__ == "__main__":
    
    new_info = {
        "Name": "Timothy Afolami",
        "Address": "Lagos, Nigeria",
        "Phone Number": "08100450227",
        "Email" : "timmyafolami8469@gmail.com"
    }
    response = insert_user_info(user_info=new_info)
    print(response)