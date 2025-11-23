from google.genai import types
try:
    print("types attributes:", dir(types))
    if hasattr(types, 'Type'):
        print("types.Type attributes:", dir(types.Type))
    else:
        print("types.Type does not exist")
except Exception as e:
    print(e)
