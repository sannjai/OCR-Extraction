import easyocr # (Optical Character Recognition)
import numpy as np
import PIL
from PIL import Image, ImageDraw
import cv2
import os
import re
import sqlalchemy
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine, inspect
import streamlit as st

st.set_page_config(layout='wide')
st.title(':blue[Business Card Data Extraction]')
tab1, tab2 = st.tabs(["Data Extraction zone", "Data modification zone"])

with tab1:
    st.subheader(':blue[Data Extraction]')
    
    import_image = st.file_uploader('**Select a business card (Image file)**', type =['png','jpg', "jpeg"], accept_multiple_files=False)
    st.markdown('''File extension support: **PNG, JPG, TIFF**, File size limit: **200 Mb**, Image dimension limit: **1500 pixel**, Language : **English**.''')
    if import_image is not None:
        try:
            # Create the reader object with desired languages
            reader = easyocr.Reader(['en'], gpu=False)

        except ImportError:
            st.info("Error: easyocr module is not installed. Please install it.")
        except Exception as e:
            st.info(f"Unexpected error occurred while creating EasyOCR reader: {e}")
        else:
            try:  
                if isinstance(import_image, str):
                    image = Image.open(import_image)
                elif isinstance(import_image, Image.Image):
                    image = import_image
                else:
                    image = Image.open(import_image)
                
                image_array = np.array(image)
                text_read = reader.readtext(image_array)

                result = []
                for text in text_read:
                    result.append(text[1])

            except Exception as e:
                st.info(f"Error: Failed to process the image. Please try again with a different image. Details: {e}")

            col1, col2= st.columns(2)

            with col1:
                
                def draw_boxes(image, text_read, color='yellow', width=2):

                    # bounding boxes
                    image_with_boxes = image.copy()
                    draw = ImageDraw.Draw(image_with_boxes)
                    
                    # draw boundaries
                    for bound in text_read:
                        p0, p1, p2, p3 = bound[0]
                        draw.line([*p0, *p1, *p2, *p3, *p0], fill=color, width=width)
                    return image_with_boxes

                # Function calling
                result_image = draw_boxes(image, text_read)

                # Result image
                st.image(result_image, caption='Captured text')
            with col2:
            # Initialize the data dictionary
                data = {
                    "Company_name": [],
                    "Card_holder": [],
                    "Designation": [],
                    "Mobile_number": [],
                    "Email": [],
                    "Website": [],
                    "Area": [],
                    "City": [],
                    "State": [],
                    "Pin_code": [],
                    }
                def get_data(res):
                    city = ""
                    for ind,i in enumerate(res):

                  
                    # To get WEBSITE_URL
                        if "www " in i.lower() or "www." in i.lower():
                            data["Website"].append(i)
                        elif "WWW" in i:
                            data["Website"].append(res[ind-1] + "." + res[ind])

                        # To get EMAIL ID
                        elif "@" in i:
                            data["Email"].append(i)

                        # To get MOBILE NUMBER
                        elif "-" in i:
                            data["Mobile_number"].append(i)
                            if len(data["Mobile_number"]) == 2:
                                data["Mobile_number"] = " & ".join(data["Mobile_number"])

                        # To get COMPANY NAME
                        elif ind == len(res) - 1:
                            data["Company_name"].append(i)

                        # To get CARD HOLDER NAME
                        elif ind == 0:
                            data["Card_holder"].append(i)

                        # To get DESIGNATION
                        elif ind == 1:
                            data["Designation"].append(i)

                        # To get AREA
                        if re.findall("^[0-9].+, [a-zA-Z]+", i):
                            data["Area"].append(i.split(",")[0])
                        elif re.findall("[0-9] [a-zA-Z]+", i):
                            data["Area"].append(i)

                        # To get CITY NAME
                        match1 = re.findall(".+St , ([a-zA-Z]+).+", i)
                        match2 = re.findall(".+St,, ([a-zA-Z]+).+", i)
                        match3 = re.findall("^[E].*", i)
                        if match1:
                            city = match1[0]  # Assign the matched city value
                        elif match2:
                            city = match2[0]  # Assign the matched city value
                        elif match3:
                            city = match3[0]  # Assign the matched city value

                        # To get STATE
                        state_match = re.findall("[a-zA-Z]{9} +[0-9]", i)
                        if state_match:
                            data["State"].append(i[:9])
                        elif re.findall("^[0-9].+, ([a-zA-Z]+);", i):
                            data["State"].append(i.split()[-1])
                        if len(data["State"]) == 2:
                            data["State"].pop(0)

                        # To get PINCODE
                        if len(i) >= 6 and i.isdigit():
                            data["Pin_code"].append(i)
                        elif re.findall("[a-zA-Z]{9} +[0-9]", i):
                            data["Pin_code"].append(i[10:])

                    data["City"].append(city) 
                get_data(result)
                data_df = pd.DataFrame(data)
            

                    # Show dataframe
                st.dataframe(data_df.T)

            class SessionState:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)
            session_state = SessionState(data_uploaded=False)

            # Upload button
            st.write('Click the :red[**Upload to MySQL DB**] button to upload the data')
            Upload = st.button('**Upload to MySQL DB**', key='upload_button')

            # Check if the button is clicked
            if Upload:
                session_state.data_uploaded = True


            if session_state.data_uploaded:
        # Connect to the MySQL server
                connect = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="Sannjai@23",
                    database = "bizcard"
                )
                cursor = connect.cursor()
                cursor.execute('''CREATE TABLE IF NOT EXISTS card_data
                   (
                    company_name TEXT,
                    card_holder TEXT,
                    designation TEXT,
                    mobile_number VARCHAR(50),
                    email TEXT,
                    website TEXT,
                    area TEXT,
                    city TEXT,
                    state TEXT,
                    pin_code VARCHAR(10)
                    
                    )''')
                for index, row in data_df.iterrows():
                    company_name = row['Company_name']
    
                    # Check if a record with the same Company_name exists
                    cursor.execute("SELECT * FROM card_data WHERE company_name = %s", (company_name,))
                    existing_record = cursor.fetchall()
                    
                    # If such a record exists, delete it
                    if existing_record:
                        cursor.execute("DELETE FROM card_data WHERE company_name = %s", (company_name,))
                        st.write(f"Deleted existing record for Company_name: {company_name}")
    
                    
                    # Insert the new record from the DataFrame
                    cursor.execute('''
                        INSERT INTO card_data (
                            company_name, card_holder, designation, mobile_number, email, website, area, city, state, pin_code
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        row['Company_name'], row['Card_holder'], row['Designation'], row['Mobile_number'],
                        row['Email'], row['Website'], row['Area'], row['City'], row['State'], row['Pin_code']
                    ))

                # Commit the transaction
                    connect.commit()

                    # Close the cursor and connection
                    cursor.close()
                    connect.close()

                    
                st.write("Data inserted successfully!")

with tab2:     
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(':red[Edit option]')
        try:
            # Connect to the database
            connect = mysql.connector.connect(
                host="localhost",
                user="root",
                password="Sannjai@23",
                database="bizcard"
            )
            cursor = connect.cursor()

            # Fetch all cardholder names
            cursor.execute("SELECT card_holder FROM card_data")
            rows = cursor.fetchall()
            names = [row[0] for row in rows]

            # Create a selection box to select cardholder name
            cardholder_name = st.selectbox("**Select a Cardholder name to Edit the details**", names, key='cardholder_name')

            # Fetch the details of the selected cardholder
            cursor.execute("SELECT Company_name, Card_holder, Designation, Mobile_number, Email, Website, Area, City, State, Pin_code FROM card_data WHERE card_holder = %s", (cardholder_name,))
            col_data = cursor.fetchone()  # Fetch one row

            if col_data:
                # Display the current values in text inputs
                Company_name = st.text_input("Company name", col_data[0])
                Card_holder = st.text_input("Cardholder", col_data[1])
                Designation = st.text_input("Designation", col_data[2])
                Mobile_number = st.text_input("Mobile number", col_data[3])
                Email = st.text_input("Email", col_data[4])
                Website = st.text_input("Website", col_data[5])
                Area = st.text_input("Area", col_data[6])
                City = st.text_input("City", col_data[7])
                State = st.text_input("State", col_data[8])
                Pin_code = st.text_input("Pincode", col_data[9])
              
                st.write('Click the :red[**Update**] button to update the modified data')
                update = st.button('**Update**', key='update')

                if update:
                    # Update the record in the database
                    cursor.execute('''
                        UPDATE card_data 
                        SET company_name = %s, designation = %s, mobile_number = %s, email = %s, 
                            website = %s, area = %s, city = %s, state = %s, pin_code = %s 
                        WHERE card_holder = %s
                    ''', (Company_name, Designation, Mobile_number, Email, Website, Area, City, State, Pin_code, Card_holder))

                    connect.commit()
                    st.success("Successfully Updated.")

            else:
                st.info('No data found for the selected cardholder.')

        except mysql.connector.Error as err:
            st.error(f"Error: {err}")

        finally:
            cursor.close()
            connect.close()


    with col2:
        st.subheader(':red[delete option]')
        try:
        # Connect to the database
            connect = mysql.connector.connect(
                host="localhost",
                user="root",
                password="Sannjai@23",
                database="bizcard"
            )
            cursor = connect.cursor()

            # Fetch all cardholder names
            cursor.execute("SELECT card_holder FROM card_data")
            rows = cursor.fetchall()
            del_names = [row[0] for row in rows]

            # Create a selection box for cardholder names
            delete_name = st.selectbox("**Select a Cardholder name to Delete the details**", del_names, key='delete_name')

            st.write('Click the :red[**Delete**] button to delete the selected cardholder details')
            delet = st.button('**Delete**', key='delet')

            if delet:
                # Execute the deletion query
                cursor.execute("DELETE FROM card_data WHERE card_holder = %s", (delete_name,))
                connect.commit()
                st.success("Successfully deleted from database.")

            # Close the database connection
            cursor.close()
            connect.close()

        except Exception as e:
            st.error(f'An error occurred: {e}')