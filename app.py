import pymysql
import streamlit as st
from datetime import datetime, time
import pandas as pd
import json
import requests

# cache so it doesn't rerun every time a widget changes
# given a start date and end date, fetch all tracking numbers within that date from the db 
@st.cache_data
def fetch_data(start_date, end_date):
  # connect to the SQL database with the enviroment variables 
  conn = pymysql.connect(
    host=str(st.secrets.MYSQL_HOST),
    port=int(st.secrets.MYSQL_PORT),
    user=str(st.secrets.MYSQL_USERNAME),
    password=str(st.secrets.MYSQL_PASSWORD),
    database=str(st.secrets.MYSQL_DATABASE),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
  )
  rows = []
  try:
    # instead of cur = conn.cursor() because with automatically closes
    with conn.cursor() as cur:
      sql = """
          SELECT DISTINCT tracking_number, router_messages, latest_router_description, latest_router_time
          FROM transit_third_party_caches
          WHERE created_at >= %s AND created_at < %s
      """
      # convert to datetime object 
      start_dt = datetime.combine(start_date, time.min)
      end_dt   = datetime.combine(end_date, time.max)
      cur.execute(sql, (start_dt, end_dt))
    # could use fetchmany but lazy? not enough rows to do so?
    rows = cur.fetchall()
  finally:
      conn.close()
  return rows 

def parse_driver_name(row):
  if row['router_messages'] == "":
    placeholder.write("no router_messages")
    return "no router_messages"
  else: 
    router_messages = json.loads(row['router_messages'])
    logs = router_messages["listItemReadableStatusLogs"]
    last = logs[len(logs)-1]
    driver_id = last["pod"]["listAssigneeId"]
    result = st.session_state.driver_list[st.session_state.driver_list['listAssigneeId'] == driver_id]
    if result.empty:
      placeholder.write("no driver ID")
      return "no driver ID"
    else:
      placeholder.write(result.iloc[0]["name"])
      return result.iloc[0]["name"]

def parse_dsp(row):
  split = row["driver name"].split("-")
  dsp = split[0].strip()
  placeholder.write(dsp)
  return dsp

def fetch_driver_list():
  headers = {"Authorization": st.secrets.API_TOKEN}
  url = "https://isp.beans.ai/enterprise/v1/lists/assignees"
  response = requests.get(url, headers=headers)
  return response.json()["assignee"]

# start and end date picker
start_date = st.date_input("pick start date")
end_date = st.date_input("pick end date")
st.write("start date:", start_date, "end date:", end_date) 

# button to fetch from db & write the response 
# use session state so it doesn't rerun 
if st.button("fetch from db"):
  st.session_state.data = pd.DataFrame(fetch_data(start_date, end_date))
if "data" in st.session_state:
  st.write(st.session_state.data)

#if st.button("load test data"):
#  st.session_state.data = pd.read_csv("testdata.csv").head()

if st.button("load driver list"):
  st.session_state.driver_list = pd.DataFrame(fetch_driver_list())
if "driver_list" in st.session_state:
  st.write(st.session_state.driver_list)

if st.button("parse driver names"):
  placeholder = st.empty()
  st.session_state.data["driver name"] = st.session_state.data.apply(parse_driver_name, axis = 1)
  st.session_state.data["dsp"] = st.session_state.data.apply(parse_dsp, axis = 1)
  st.write(st.session_state.data)

filter_dsp = st.text_input("dsp filter")
if filter_dsp:
  st.write(st.session_state.data[st.session_state.data['dsp'] == filter_dsp])