import pickle 
db_file = r"E:\Email_tool\DataBase_Training_files\Chicago, IL-77000.pkl"

with open(db_file, "rb") as file:
    data_dict = pickle.load(file)  # Load as a dictionary

# Print or use the dictionary

# Loop through dictionary
# for key, value in data_dict.items():
#     print(f"{key}: {value}")
print (data_dict)
print(len(data_dict))