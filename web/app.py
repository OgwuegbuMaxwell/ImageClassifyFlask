from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient

import bcrypt
import numpy as np
import requests


from utilities import addTokens, userExist, verifyPassword, countTokens, isAdmin, verifyCredentials
from config import users


from keras.applications import InceptionV3
from keras.applications.inception_v3 import preprocess_input
from keras.applications import imagenet_utils
from tensorflow.keras.preprocessing.image import img_to_array
from PIL import Image
from io import BytesIO

# Load the pre trained model
pretrained_model = InceptionV3(weights="imagenet")






app = Flask(__name__)
api = Api(app)




# Resource to handle user registration
class Register(Resource):
    def post(self):
        postedData = request.get_json()  # Get data posted by the user
        
        username = postedData["username"]
        password = postedData["password"]
        is_admin = postedData.get("is_admin", 0)  # Default to 0 if not provided
        
        # Check if the username already exists in the database
        if userExist(username):
            retJson = {
                "status": 301,
                "msg": "Username already exists. Please choose a different username."
            }
            return jsonify(retJson)
        
        
        # Hash the password for storage
        hashed_password = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        
        # Insert the new user into the database
        users.insert_one({
            "Username": username,
            "Password": hashed_password,
            "Token": 5, # Each new user starts with 10 tokens
            "is_admin": is_admin
        })
        
        # Return a success message
        retJson = {
            "status": 200,
            "msg": "You have successfully signed up for the API"
        }
        return jsonify(retJson)
    



class Refill(Resource):
    def post(self):
        postedData = request.get_json()
        
        username = postedData["username"]
        password = postedData["password"]
        
        # User name of the user Admin want to refill the token for
        user = postedData["user"]
        # Refilling amount
        refill_amount = postedData["refill"]
        
                
        # *** Verfy Admin login detials ***
        if not userExist(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username"
            }
            return jsonify(retJson)
        
        
        # Verify if user is admin
        is_admin = isAdmin(username)
        if not is_admin:
            retJson = {
                "status": 304,
                "msg": "Warining! You are not authorized to perform this operation."
            }
            return jsonify(retJson)
            

        
        # verify Admin password
        correct_password = verifyPassword(username, password)
        if not correct_password:
            retJson = {
                "status": 304,
                "msg": "Invalid Admin Password"
            }
            return jsonify(retJson)

        
        # Verify that the user Admin wants to refill the token exist
        if not userExist(user):
            retJson = {
                "status": 301,
                "msg": "User you want to refill does not exist"
            }
            return jsonify(retJson)
        
        # Count the user's toke, the user Admin wants to refile his/token
        current_token = countTokens(user)
        
        new_token = addTokens(current_token, refill_amount)
        
        # Update the token count in the database
        users.update_one(
            {"Username": user},
            {"$set": {"Token": new_token}}
        )
        
        retJson = {
            "status": 200,
            "msg": "Refilled Successfully!"
        }
            
        return jsonify(retJson)
 


# Check user number of tokens
class Token(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData.get("username")
        password = postedData.get("password")
        
        # Verify Username
        if not userExist(username):
            retJson = {
                "status": 301,
                "msg": "Username does not exist. Register and try again."
            }
            return jsonify(retJson)
            

        # Verify user password
        correct_password = verifyPassword(username, password)
        if not correct_password:
            retJson = {
                "status": 302, 
                "msg": "Invalid Password",
            }
            return jsonify(retJson)

        # Retrieve the token count for the user
        num_tokens = countTokens(username)
        if num_tokens is None:
            retJson = {
                "status": 404, 
                "msg": "User not found"
            }
        
        # Charge the user a token for making this request
        current_tokens = countTokens(username)
        users.update_one(
            {"Username": username},
            {"$set": {"Token": current_tokens - 1}}
        )

        # Return the number of tokens
        retJson = {
            "status": 200, 
            "msg": f"You have {num_tokens} tokens remaining."
        }
        
        return jsonify(retJson)



class Classify(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData.get("username")
        password = postedData.get("password")
        url = postedData.get("url")
        
        # Use verifyCredentials to check if the username and password are correct
        if not verifyCredentials(username, password):
            retJson = {
                "status": 403,
                "msg": "Authentication failed. Please check your username and password."
            }
            
            return jsonify(retJson)
            
        
        # check if the user has tokens
        tokens = countTokens(username)
        if tokens <= 0:
            retJson = {
                "status": 303,
                "msg": "Not Enough Tokens"
            }
            return jsonify(retJson)
        
        # Check url
        if not url:
            retJson = {
                "status": 400,
                "msg": "No url provided"
            }
            return jsonify(retJson)
        
        
        '''
        # Load image from url
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        '''
        
        # Load image from url
        try:
            response = requests.get(url)
            if response.status_code != 200:
                retJson = {
                    "status": 404, 
                    "msg": "URL is not accessible"
                }
                return jsonify(retJson)
            img = Image.open(BytesIO(response.content))
        except Exception as e:
            retJson = {
                "status": 500, 
                "msg": "Failed to load image", "error": str(e)
            }
            return jsonify(retJson)

    
        
        # pre process the image
        img = img.resize((299,299)) # Resized to size expected by InceptionV3 for better result
        img_array = img_to_array(img) # Covert into numpy array
        img_array = np.expand_dims(img_array, axis=0) # set the axis to zero and the array values are sclaed appropriately
        img_array = preprocess_input(img_array)
        ### the steps above are the pre-processing steps we need to adhere to in 
        ### other to make the image perfect for prediction 
        
        # Make prediction
        prediction = pretrained_model.predict(img_array)
        actual_prediction = imagenet_utils.decode_predictions(prediction, top=5)
        
        # return classification response
        retJson = {}
        for pred in actual_prediction[0]:
            retJson[pred[1]] = float(pred[2] * 100)
            
        
        # Charge the user a token for making this request
        
        users.update_one(
            {"Username": username},
            {"$set": {"Token": tokens - 1}}
        )
        
        return jsonify(retJson)
        



api.add_resource(Register, '/register')        
api.add_resource(Classify, '/classify') 
api.add_resource(Refill, '/refill')
api.add_resource(Token, '/token')

# RUN app
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)    
