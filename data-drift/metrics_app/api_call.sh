#!/bin/bash

url="http://127.0.0.1:8085/iterate-500/"

# Make the API request
response=$(curl -s -X GET "$url")

# Log the response
echo "$(date) - Response: $response" >> /var/log/api_call.log