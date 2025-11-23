from google import genai
from config import GOOGLE_API_KEY

client = genai.Client(api_key=GOOGLE_API_KEY)

try:
    print("Listing models...")
    # The SDK might have different methods, let's try the standard one for this version
    # Based on v0.2.1, it might be client.models.list()
    for model in client.models.list():
        print(f"Model: {model.name}")
        print(f"  Supported methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
