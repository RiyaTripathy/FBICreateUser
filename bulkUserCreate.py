# import python modules

import csv
import configparser
import requests
import pandas as pd

# Read the config file to retrieve url, token and filename
config = configparser.ConfigParser()
config.read('okta-config.txt')
url = config.get('General', 'url')
token = config.get('General', 'token')
fileName = config.get('General', 'filename')


# Read CSV file and create a DataFrame
df = pd.read_csv(fileName, sep=',')

# sort the dataframe by user id
df1=df.sort_values(by=['User ID'])

# Merge data by groupby with aggregate first and custom function ';'.join:
df2 = df1.groupby('User ID').agg({'First Name':'first','Last Name':'first','email address':'first','Role Code':'first','Company Code': ';'.join,'Division Code': ';'.join,'Roundtable Code': ';'.join}).reset_index()

# write the transformed dataset to a FBIuser csv file
df2.to_csv('FBIuser.csv',index=False)

# function to create FBI user/admin in Okta with required attributes

def createStagedUser (id, login, firstName, lastName, email, Role , Company, Division, Roundtable ):

    # preparing the Create User JSON BODY
    jsonTosend = {"type": {"id": id},"profile": {"firstName": firstName, "lastName": lastName, "role_code": Role, "company": Company, "divisions": Division, "roundtable_group": Roundtable,"email": email, "login": login}}

    # Call the create user Okta API
    res = requests.post(url+'/api/v1/users?activate', headers={'Accept': 'application/json', 'Content-Type':'application/json', 'Authorization': 'SSWS '+token}, json=jsonTosend)

    # Check the status code of the response for success and failure
    if res.status_code == 200:
        with open('UserCreated.txt', 'a') as f:
            f.write(login + '\n')
    else:
        with open('UserNotCreated.txt', 'a') as f:
            f.write(login + '\n')
    return res.status_code

# Read the transformed data from the csv file

with open('FBIuser.csv','r') as File:
    reader = csv.reader(File, delimiter=',')
    next(reader)

    # Iterate over the data to store the multivalued attributes in list
    for row in reader:
        try:
            Company = row[5].split(';')
            Division = row[6].split(';')
            Roundtable = row[7].split(';')

            # call the API to retrieve the Okta user types
            res1 = requests.get(url + '/api/v1/meta/types/user',
                                headers={'Accept': 'application/json', 'Content-Type': 'application/json',
                                         'Authorization': 'SSWS ' + token})
            result=res1.json()

            # Check if the value of the Role from csv matches the Role code for FBI user
            # If matches, assign the Role variable to "FBI User" 
            if row[4] == "EXT1":
                Role = "FBI Member"

                # Iterate the response of Okta User Type API to match "FBI User" Role name with "FBI User" user type in Okta
                # Retrieve the id of the "FBI User" User type to pass it to the Create user API JSON body
                for name in result:
                    if name['displayName']==Role:
                        id=name['id']

                        # Pass the id along with the other attributes to the create user method
                        # Call user creation function
                        createStagedUser(id, row[0], row[1], row[2], row[3], row[4], Company, Division, Roundtable)

            # Check if the value of the Role from csv matches the Role code for FBI member admin
            # If matches, assign the Role variable to "FBI Member Admin" 
            elif row[4]=="EXT2":
                    Role="FBI Member Admin"

                    # Iterate response of the Okta User Type API to match "FBI Member Admin" Role name with "FBI Member Admin" user type in Okta
                    # Retrieve the id of the "FBI Member Admin" user type to pass it to the Create user API JSON body
                    for name in result:
                        if name['displayName'] == Role:
                            id = name['id']

                            # Pass the id along with the other attributes to the create user method
                            # Call user creation function
                            createStagedUser(id, row[0], row[1], row[2], row[3], row[4], Company, Division, Roundtable)


        except IndexError:
           print('Error')

