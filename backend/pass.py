import urllib.parse
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# 1. Your real username and password
my_username = "Vinu" 
my_password = "vinu@2004" # <-- PUT YOUR REAL PASSWORD HERE

# 2. (!!!) YOUR REAL CLUSTER ADDRESS (!!!)
# PASTE THE ADDRESS YOU COPIED FROM ATLAS HERE, INSIDE THE QUOTES.
YOUR_REAL_CLUSTER_ADDRESS = "cluster0.rqrww9d.mongodb.net" # <-- REPLACE THIS

# 3. Escape the username and password
escaped_username = urllib.parse.quote_plus("Vinu") # pyright: ignore[reportUndefinedVariable]
escaped_password = urllib.parse.quote_plus("vinu@2004") # pyright: ignore[reportUndefinedVariable]

# 4. Build the final, correct URI
# This line now uses the variable 'YOUR_REAL_CLUSTER_ADDRESS'
uri = f"mongodb+srv://{escaped_username }:{escaped_password}@{"ccluster0.rqrww9d.mongodb.net"}/?retryWrites=true&w=majority"

# 5. Try connecting
try:
    client = MongoClient(uri, server_api=ServerApi('1'))
    
    # Send a ping to confirm a successful connection
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")

except Exception as e:
    print(f"An error occurred: {e}")