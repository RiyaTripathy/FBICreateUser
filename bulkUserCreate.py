# import python modules

import csv
import configparser
import requests
import urllib3
import pandas as pd


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Read the config file to retrieve url, token and filename
config = configparser.ConfigParser()
config.read('okta-config.txt')
url = config.get('General', 'url')
token = config.get('General', 'token')
fileName = config.get('General', 'filename')
FBIMember = config.get('General', 'group_name')
FBIMemberAdmin = config.get('General', 'group_name1')


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

    # Stripping whitespaces from Company , Division and Roundtable values

    Company = [x.strip(' ') for x in Company]
    CompanySet = set(Company)
    UniqueCompany=list(CompanySet)
    Division = [x.strip(' ') for x in Division]
    DivisionSet = set(Division)
    UniqueDivision = list(DivisionSet)
    Roundtable = [x.strip(' ') for x in Roundtable]
    RoundtableSet = set(Roundtable)
    UniqueRoundtable = list(RoundtableSet)

    # preparing the Create User JSON BODY
    jsonTosend = {"type": {"id": id},"profile": {"firstName": firstName.lstrip().rstrip(), "lastName": lastName.lstrip().rstrip(), "role_code": Role.lstrip().rstrip(), "company": UniqueCompany, "divisions": UniqueDivision, "roundtable_group": UniqueRoundtable,"email": email.lstrip().rstrip(), "login": login.lstrip().rstrip()}}

    # Call the create user Okta API
    res = requests.post(url+'/api/v1/users?activate', headers={'Accept': 'application/json', 'Content-Type':'application/json', 'Authorization': 'SSWS '+token}, json=jsonTosend, verify=False)

    response = res.json()

    # Check the status code of the response for success and failure
    if res.status_code == 200:

        # Add the userid of the created user to a file for record
        with open('UserCreated.txt', 'a') as f:
            f.write(login.lstrip().rstrip() + '\n')
            dict = res.json()

            # Getting the id of the created user
            userId = dict['id']

            # Getting the Role of the created user
            Role = dict['profile']['role_code']

            # Check if the Role_Code is EXT1, Get the groupID of FBI Member group to add the user to the FBI Member group
            if Role == 'EXT1':

                #Call the Search Group API to retrive the GroupID of FBI Member group
                res = requests.get(url + '/api/v1/groups?q=' + FBIMember,
                               headers={'Accept': 'application/json', 'Content-Type': 'application/json',
                                        'Authorization': 'SSWS ' + token},verify=False)
                dictFromServer = res.json()
                groupId = dictFromServer[0]['id']

                # Call the API to add the user to the FBI Member Group
                res = requests.put(url + '/api/v1/groups/' + groupId + '/users/' + userId,
                               headers={'Accept': 'application/json', 'Content-Type': 'application/json',
                                        'Authorization': 'SSWS ' + token},verify=False)

            # Check if the Role_Code is EXT2, Get the groupID of FBI Member Admin group to add the user to the FBI Member Admin group
            elif Role == 'EXT2':

                # Call the Search Group API to retrive the GroupID of FBI Member Admin group
                res = requests.get(url + '/api/v1/groups?q=' + FBIMemberAdmin,
                               headers={'Accept': 'application/json', 'Content-Type': 'application/json',
                                        'Authorization': 'SSWS ' + token},verify=False)
                dictFromServer = res.json()
                groupId = dictFromServer[0]['id']

                # Call the API to add the user to the FBI Member Admin Group
                res = requests.put(url + '/api/v1/groups/' + groupId + '/users/' + userId,
                               headers={'Accept': 'application/json', 'Content-Type': 'application/json',
                                        'Authorization': 'SSWS ' + token},verify=False)

    # Add the userid and error summary of the users not created to a csv file for record
    else:
      with open('UserNotCreated.csv', mode='a') as f:
          error = str(response['errorCauses'])
          writer = csv.writer(f, delimiter=',')
          writer.writerow([login.lstrip().rstrip(), error[19:-3]])
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
                                         'Authorization': 'SSWS ' + token},verify=False)
            result=res1.json()

            # Check if the value of the Role from csv matches the Role code for FBI user
            # If matches, assign the Role variable to "FBI User"
            if row[4].lstrip().rstrip() == "EXT1":
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
            elif row[4].lstrip().rstrip()=="EXT2":
                    Role="FBI Member Admin"

                    # Iterate response of the Okta User Type API to match "FBI Member Admin" Role name with "FBI Member Admin" user type in Okta
                    # Retrieve the id of the "FBI Member Admin" user type to pass it to the Create user API JSON body
                    for name in result:
                        if name['displayName'] == Role:
                            id = name['id']

                            # Pass the id along with the other attributes to the create user method
                            # Call user creation function
                            createStagedUser(id, row[0], row[1], row[2], row[3], row[4], Company, Division, Roundtable)
            else:
                with open('UserNotCreated.txt', 'a') as f:
                    f.write(str(row[0]) + ' Role Code Not in Scope '+ str(row[4]) + '\n')

        except IndexError:
           print('Error')
