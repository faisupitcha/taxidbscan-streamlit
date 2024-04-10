import folium.features
import streamlit as st
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import silhouette_score
from shapely.geometry import Point
from streamlit_folium import st_folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
from sklearn.cluster import DBSCAN
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import geopandas as gpd
import pandas as pd
import numpy as np
import geopandas
import random
import requests
import gzip
import math
import folium
import json
import utm

###Set the streamlit page layout
st.set_page_config(
    page_title="DBSCAN Clustering (Wed)",
    page_icon="📁",
    layout="wide"
)

@st.cache_data
def latlon2EN(filtered_mon):
    taxi_data_subset = filtered_mon.loc[:, ['startlat', 'startlon','timeintrip']]
    taxi_data_subset['utm'] = taxi_data_subset.apply(lambda row: utm.from_latlon(row["startlat"], row["startlon"]), axis=1)
    utm_cols = ['easting', 'northing', 'zone_number', 'zone_letter']
    for n, col in enumerate(utm_cols):
        taxi_data_subset[col] = taxi_data_subset['utm'].apply(lambda location: location[n])
    taxi_data_subset = taxi_data_subset.drop('utm', axis=1)
    return taxi_data_subset

@st.cache_data
def get_point(taxi_data_subset):
    points = taxi_data_subset[['easting', 'northing']].values.tolist()
    points = np.array(points)
    return points

@st.cache_data
def minpts(points):
    #count the number of rows then define the number of MinPts
    MinPts = math.floor(np.log(len(points)))
    return MinPts

# Function to plot nearest neighbor distances
@st.cache_data
def plot_nn_distances(distances):
    # สร้างกราฟเส้นด้วย Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=np.arange(len(distances)), y=distances, mode='lines', name='Nearest Neighbor Distance'))

    # กำหนดรายละเอียดแกนและชื่อกราฟ
    fig.update_layout(
        xaxis_title='Points',
        yaxis_title='Nearest Neighbor Distance',
        title='Nearest Neighbor Distances'
    )
    fig.update_layout(width=600, height=500)

    # แสดงกราฟใน Streamlit
    st.plotly_chart(fig)
    # fig, ax = plt.subplots()  # สร้างรูปภาพด้วย matplotlib
    # ax.plot(distances)
    # ax.set_xlabel('Points')
    # ax.set_ylabel('Nearest Neighbor Distance')
    # ax.set_title('Nearest Neighbor Distances')
    # st.pyplot(fig)  # แสดงรูปภาพใน Streamlit

    # plt.plot(distances)
    # plt.xlabel('Points')
    # plt.ylabel('Nearest Neighbor Distance')
    # plt.title('Nearest Neighbor Distances')
    # st.pyplot()

# แปลงไฟล์ geopandas -> dataframe
@st.cache_data
def geodf_to_str(_geodf):
    # สร้าง GeoDataFrame ตัวอย่าง
    # gdf = gpd.read_file(_geodf)
    # แปลง GeoDataFrame เป็น DataFrame โดยลบคอลัมน์ geometry
    df = pd.DataFrame(_geodf)
    df = df.drop(columns='geometry')
    return df

# *******************************************************************************************************************

top_10_districts = ["เขตจตุจักร","เขตราชเทวี","เขตบางกอกน้อย","เขตปทุมวัน","เขตดุสิต","เขตพระนคร","เขตหลักสี่","เขตดอนเมือง","เขตบางนา","เขตยานนาวา"]

# โหลด DataFrame ข้อมูล Taxi วันจัน กรุงเทพ
# taxi_data = pd.read_csv('D:\Senior Project\OD_2022\Wednesday_bkk.csv')
with gzip.open('../Wednesday2_bkk.gz', 'rb') as f:
    # อ่านข้อมูลเข้าสู่ DataFrame ของ pandas
    taxi_data = pd.read_csv(f)

# ข้อมูลเขตกรุงเทพ
url = "https://github.com/pcrete/gsvloader-demo/raw/master/geojson/Bangkok-districts.geojson"
response = requests.get(url)
data = response.json()
states = geopandas.GeoDataFrame.from_features(data, crs="EPSG:4326")

# *******************************************************************************************************************

st.title("CLUSTER BY DBSCAN ON Wednesday")
st.markdown("After selecting the district, start time, and end time, you will get a Nearest Neighbor Distance graph to use as a reference for finding the eps value in the 'Clustering' tab. This tab will display the clustering results obtained.")
st.markdown("The principle of selecting the START RANGE and END RANGE is to choose from the range of y-axis values where the graph starts to slope upwards until it becomes a straight line.")

st.markdown("Please select district below and then click view results")

tab1, tab2 = st.tabs(["Nearest Neighbor Distance","Clustering"])

with tab1:

    with st.form("my form"):

        selected = st.selectbox("CHOOSE DISTRICT",top_10_districts)
        # selected.to_file("selected.shp")
        # with open("selected.txt", "w") as file:
        #     # Write text to the file
        #     file.write("selected")

        num_start = st.selectbox("ENTER STARTTIME", list(range(25)), format_func=lambda x: str(x) if x != 0 else "Choose start time")
        num_end = st.selectbox("ENTER ENDTIME", list(range(1, 25)), format_func=lambda x: str(x) if x != 0 else "Choose end time")
        # num_start = st.sidebar.number_input("ENTER STARTTIME", min_value=0, max_value=24, value=1)
        # num_end = st.sidebar.number_input("ENTER ENDTIME", min_value=1, max_value=24, value=num_start + 1)

        submitted = st.form_submit_button("view results")
        
        if submitted:
            # เลือกช่วงเวลา
            taxi_data['starttime'] = pd.to_datetime(taxi_data['starttime'])
            # st.write("Shape of taxi_data:", taxi_data.shape)

            filtered_mon = taxi_data[(taxi_data['starttime'].dt.hour >= num_start) & (taxi_data['starttime'].dt.hour < num_end)]
            # st.write("filtered_mon:", filtered_mon.shape)

            # นำข้อมูลของเขตที่ผู้ใช้เลือกจาก states มาเก็บไว้ในตัวแปร selected_district
            selected_district = states[states['dname'] == selected]
            selected_district.to_file("selected_district.shp")
            # st.write("selected_district:", selected_district.shape)

            # สร้าง GeoDataFrame จาก DataFrame ที่มีคอลัมน์ lat และ lon
            geometry = [Point(lon, lat) for lat, lon in zip(filtered_mon['startlat'], filtered_mon['startlon'])]
            filtered_mon_geo = gpd.GeoDataFrame(filtered_mon, geometry=geometry)
            filtered_mon_in_selected_district = filtered_mon_geo[filtered_mon_geo['geometry'].within(selected_district.unary_union)]
            # st.write("filtered_mon_in_selected_district:", filtered_mon_in_selected_district.shape)

            taxi_subset = latlon2EN(geodf_to_str(filtered_mon_in_selected_district))
            taxi_subset.to_csv("taxi_subset.csv", encoding="utf-8")

            # สร้าง point เพื่อไปหาพารามิเตอร์
            # st.write("geodf_to_str(filtered_mon_in_selected_district):", geodf_to_str(filtered_mon_in_selected_district).shape)

            points = get_point(latlon2EN(geodf_to_str(filtered_mon_in_selected_district)))
            # st.write(points)
            # st.write("points:", points.shape)
            np.savetxt('points.txt', points)

            col8, col9= st.columns(2, gap='large')

            with col8:
                # สร้างแผนที่ folium ด้วยตำแหน่งเริ่มต้น
                mm = folium.Map(location=[13.7563, 100.5018], tiles="OpenStreetMap", zoom_start=14)

                # เพิ่มข้อมูลขอบเขตเขตที่ผู้ใช้เลือกลงในแผนที่
                choropleth = folium.Choropleth(
                    geo_data=selected_district.to_json(),
                    data=selected_district,
                    columns=('dname', 'AREA'),
                    key_on='feature.properties.dname',
                    line_opacity=0.8,
                    highlight=True
                )
                choropleth.geojson.add_to(mm)

                # สร้าง Marker Cluster เพื่อจัดกลุ่มข้อมูล Marker ไว้ในกรณีที่มีจำนวนมาก
                marker_cluster = MarkerCluster().add_to(mm)

                # เพิ่มจุดของแต่ละเที่ยวรถเช่าลงในแผนที่ folium โดยใช้คอลัมน์ geometry เพื่อระบุตำแหน่ง
                for idx, row in filtered_mon_in_selected_district.iterrows():
                    folium.CircleMarker(location=[row.geometry.y, row.geometry.x],
                                        radius=2,
                                        fill=True,
                                        color='#FF0000',
                                        fill_opacity=0.7, 
                                        popup=row['starttime']).add_to(marker_cluster)

                # หาตำแหน่งขอบเขตของเขตที่ผู้ใช้เลือก
                min_lon, min_lat, max_lon, max_lat = selected_district.total_bounds

                # ซูมแผนที่เข้าไปในพื้นที่ที่สนใจ
                mm.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

                # แสดงแผนที่ folium บน Streamlit
                folium_static(mm)


            # # สร้างแผนที่ folium ด้วยตำแหน่งเริ่มต้น
            # mm = folium.Map(location=[13.7563, 100.5018], tiles="OpenStreetMap", zoom_start=14)

            # # เพิ่มข้อมูลขอบเขตเขตที่ผู้ใช้เลือกลงในแผนที่
            # choropleth = folium.Choropleth(
            #     geo_data=selected_district.to_json(),
            #     data=selected_district,
            #     columns=('dname', 'AREA'),
            #     key_on='feature.properties.dname',
            #     line_opacity=0.8,
            #     highlight=True
            # )
            # choropleth.geojson.add_to(mm)

            # # สร้าง Marker Cluster เพื่อจัดกลุ่มข้อมูล Marker ไว้ในกรณีที่มีจำนวนมาก
            # marker_cluster = MarkerCluster().add_to(mm)

            # # เพิ่มจุดของแต่ละเที่ยวรถเช่าลงในแผนที่ folium โดยใช้คอลัมน์ geometry เพื่อระบุตำแหน่ง
            # for idx, row in filtered_mon_in_selected_district.iterrows():
            #     folium.CircleMarker(location=[row.geometry.y, row.geometry.x],
            #                         radius=2,
            #                         fill=True,
            #                         color='#FF0000',
            #                         fill_opacity=0.7, 
            #                         popup=row['starttime']).add_to(marker_cluster)

            # # หาตำแหน่งขอบเขตของเขตที่ผู้ใช้เลือก
            # min_lon, min_lat, max_lon, max_lat = selected_district.total_bounds

            # # ซูมแผนที่เข้าไปในพื้นที่ที่สนใจ
            # mm.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

            # # แสดงแผนที่ folium บน Streamlit
            # folium_static(mm)

            with col9:
                # สร้างกราฟเพื่อหาค่า eps
                neighbors = NearestNeighbors(n_neighbors=minpts(points))
                neighbors_fit = neighbors.fit(points)
                distances, _ = neighbors_fit.kneighbors(points)
                distances = np.sort(distances, axis=0)
                distances = distances[:,1]

                # Plot nearest neighbor distances
                plot_nn_distances(distances)

with tab2:

    with st.form("form"):

        range_start = st.number_input("ENTER START RANGE")
        range_end = st.number_input("ENTER END RANGE")

        submitted = st.form_submit_button("view results")
        
        # กำหนดช่วงของ eps และ minPts
        eps_range = np.arange(range_start, range_end, 1)

        # if 'points' in st.session_state:
        #     points = st.session_state['points']
        
        # st.write(st.session_state['points'])

        if submitted:

            points = np.loadtxt('points.txt')
            # st.write(points)
            # st.write("points:", points.shape)

            # เก็บผลลัพธ์ที่ดีที่สุด
            best_eps = None
            best_minPts = minpts(points)
            best_silhouette_score = -1  # ค่าเริ่มต้นเป็นค่าที่ต่ำที่สุด

            # ทำลูปเพื่อทดลอง hyperparameters ทั้งหมด
            for eps in eps_range:
                # สร้างและใช้งาน DBSCAN
                dbscan = DBSCAN(eps=eps, min_samples=best_minPts)
                dbscan.fit(points)
                    
                # คำนวณ silhouette score
                labels = dbscan.labels_
                silhouette_avg = -1 if len(set(labels)) <= 1 else silhouette_score(points, labels)
                
                core_samples_mask = np.zeros_like(dbscan.labels_, dtype=bool)
                core_samples_mask[dbscan.core_sample_indices_] = True

                # คำนวณจำนวนของคลัสเตอร์
                dblabels = dbscan.labels_
                n_clusters_ = len(set(dblabels)) - (1 if -1 in dblabels else 0)

                # เก็บค่า hyperparameters ที่ให้ผลลัพธ์ที่ดีที่สุด
                if silhouette_avg > best_silhouette_score and n_clusters_ >= 3:
                    best_silhouette_score = silhouette_avg
                    best_eps = eps

            # พิมพ์ค่า hyperparameters ที่ดีที่สุด
            # st.write("Best eps:", best_eps)
            # st.write("Best minPts:", best_minPts)
            # st.write("Best silhouette score:", best_silhouette_score)

            # input parameter
            db = DBSCAN(eps=best_eps, min_samples=best_minPts).fit(points)
            core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
            core_samples_mask[db.core_sample_indices_] = True
            dblabels = db.labels_
            n_clusters_ = len(set(dblabels)) - (1 if -1 in dblabels else 0)
            n_noise_ = list(dblabels).count(-1)
                
            # คำนวณ Silhouette Score
            silhouette_avg = silhouette_score(points, dblabels)

            title = ["Best Eps","Best MinPts","Best silhouette score","N_Cluster","N_Noise"]
            
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric(title[0], best_eps)
            with col2:
                st.metric(title[1], best_minPts)
            with col3:
                st.metric(title[2], round(best_silhouette_score, 5))
            with col4:
                st.metric(title[3], n_clusters_)
            with col5:
                st.metric(title[4], n_noise_)

            # st.write("N_Cluster:", n_clusters_)
            # st.write("N_Noise:", n_noise_)

            # st.pyplot(plt.figure(figsize=(10, 8)))
            # plt.scatter(taxi_data_subset['easting'], taxi_data_subset['northing'], c=taxi_data_subset['dblabels'], cmap='plasma', s=20)
            # st.pyplot()

            filtered_mon_in_selected_district = pd.read_csv('taxi_subset.csv', encoding="utf8")
            filtered_mon_in_selected_district['cluster'] = dblabels
            # st.write(filtered_mon_in_selected_district)

            selected_district = gpd.read_file("selected_district.shp", encoding="utf-8")
            # st.write(selected_district)

            # with open("selected.txt", "r") as file:
            #     # Read the entire content of the file
            #     selected = file.read()
            # selected_district = states[states['dname'] == selected]

            col6, col7 = st.columns(2)
            
            with col6:

                # สร้าง folium Map
                colors = ['#' + ''.join(random.choices('0123456789ABCDEF', k=6)) for _ in range(n_clusters_)] # range = n_clusters_

                map_center = [filtered_mon_in_selected_district['startlat'].mean(), filtered_mon_in_selected_district['startlon'].mean()]
                my_map = folium.Map(location=map_center, zoom_start=12)

                choropleth = folium.Choropleth(
                    geo_data = selected_district.to_json(),
                    data=selected_district,
                    columns=('dname_e', 'AREA'),
                    key_on='feature.properties.dname_e',
                    line_opacity=0.8,
                    highlight=True
                )
                choropleth.geojson.add_to(my_map)
                choropleth.geojson.add_child(
                    folium.features.GeoJsonTooltip(['dname_e'], labels=False)  # แก้เป็นชื่อคอลัมน์ที่ถูกต้อง
                )

                for index, row in filtered_mon_in_selected_district.iterrows():
                    point = [row['startlat'], row['startlon']]
                    cluster = row['cluster']  # ใช้ค่า cluster จาก DataFrame
                    folium.CircleMarker(location=point, radius=3, color=colors[int(cluster)], fill=True, fill_color=colors[int(cluster)]).add_to(my_map)
                    # label = labels[index]  # ใช้ index เพื่อรับค่า label ที่เกี่ยวข้องกับแถวนั้น
                    # folium.CircleMarker(location=point, radius=3, color=colors[int(row["cluster"])], fill=True, fill_color=colors[int(row["cluster"])]).add_to(my_map)
            
                # หาตำแหน่งขอบเขตของเขตที่ผู้ใช้เลือก
                min_lon, min_lat, max_lon, max_lat = selected_district.total_bounds

                # ซูมแผนที่เข้าไปในพื้นที่ที่สนใจ
                my_map.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

                st_map = st_folium(my_map, width=700, height=450)

            with col7:
                dblabels_count = filtered_mon_in_selected_district['cluster'].value_counts()       
                fig = px.bar(x=dblabels_count.index, y=dblabels_count.values)
                fig.update_layout(xaxis_title='Cluster', yaxis_title='Number of Taxi')
                fig.update_traces(marker_color='deepskyblue')
                fig.update_layout(width=600, height=500)
                fig.update_layout(xaxis=dict(tickmode='linear', dtick=1)) 
                st.plotly_chart(fig)

st.cache_data.clear()
