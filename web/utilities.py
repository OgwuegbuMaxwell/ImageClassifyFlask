

from config import users
import bcrypt

# Check whether user exist
def userExist(username):
    return bool(users.find_one({"Username": username}))



# Helper function to verify the hashed password
def verifyPassword(username, password):
    if not userExist(username):  # Utilizing userExist to check if user exists
        return False  # Return False immediately if user does not exist

    user_data = users.find_one({"Username": username})  # Retrieves a single document
    hashed_password = user_data["Password"]
    # Check if the hashed password matches
    if bcrypt.hashpw(password.encode('utf8'), hashed_password) == hashed_password:
        return True
    return False


def verifyCredentials(username, password):
    # Check if the user exists
    if not userExist(username):
        return False  # User does not exist
    
    # Verify the password
    if not verifyPassword(username, password):
        return False  # Password does not match
    
    return True  # Both username exists and password matches

    


# Helper function to retrieve the token count for a user
def countTokens(username):
    user_data = users.find_one({"Username": username})  # Retrieves a single document
    if user_data:
        tokens = user_data["Token"]
        return tokens
    return 0  # Default token count if user is not found



# Function to refill user's token
def addTokens(current_token, refill_amount):

    # add the current token and the refill amount
    new_token_count = int(current_token) + int(refill_amount)
    
    return new_token_count



# Check if user is admin
def isAdmin(username):
    """
    Check if the specified user is an admin.
    
    Args:
    username (str): The username of the user to check.
    
    Returns:
    bool: True if the user is an admin, False otherwise.
    """
    user_data = users.find_one({"Username": username})
    if user_data and user_data.get("is_admin") == 1:
        return True
    return False

