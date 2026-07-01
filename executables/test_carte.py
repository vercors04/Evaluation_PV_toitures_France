import folium
import geopandas as gpd
import pandas as pd
from folium.plugins import Geocoder, FastMarkerCluster

map = folium.Map(location=(46.862725, 2.287592),zoom_start=6.2)

folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Vue Satellite',
    overlay=False,
    control=True,
    show=False
).add_to(map)

css_menu = """
<style>
.leaflet-control-layers {
    font-size: 18px;
    line-height: 2.5;
    padding: 20px;
    width: 320px;
    border-radius: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    background-color: rgba(255, 255, 255, 0.95);
}
.leaflet-control-layers-list input[type="checkbox"] {
    transform: scale(1.8);
    margin-right: 15px;
    cursor: pointer;
}
.leaflet-control-layers-label {
    cursor: pointer;
    font-family: Arial, sans-serif;
}
</style>
"""
map.get_root().html.add_child(folium.Element(css_menu))

titre_html = '''
<div style="position: fixed; 
            top: 20px; left: 50%; transform: translateX(-50%); width: auto; 
            background-color: rgba(255, 255, 255, 0.98); 
            border-radius: 30px; 
            z-index: 9999; padding: 10px 25px; 
            font-family: 'Helvetica Neue', Arial, sans-serif; 
            font-size: 16px; letter-spacing: 0.5px; color: #1A252C; 
            box-shadow: 0 4px 24px rgba(0,0,0,0.15);
            border: 1px solid rgba(0,0,0,0.05);">
    <span style="color: #E67E22; font-weight: bold; margin-right: 8px;">●</span>Évaluation du Potentiel Photovoltaïque des Toitures en France
</div>
'''

map.get_root().html.add_child(folium.Element(titre_html))

video_html = '''
<div style="position: fixed; 
            bottom: 20px; right: 20px; 
            width: 320px; 
            background-color: rgba(255, 255, 255, 0.98); 
            border-radius: 12px; 
            z-index: 9999; padding: 12px; 
            font-family: 'Helvetica Neue', Arial, sans-serif; 
            box-shadow: 0 4px 24px rgba(0,0,0,0.15);
            border: 1px solid rgba(0,0,0,0.05);">
    <div style="font-size: 13px; font-weight: bold; color: #1A252C; margin-bottom: 8px; text-align: center;">
        Introduction
    </div>
    <video width="100%" controls style="border-radius: 6px;">
        <source src="data/raw/introduction.mp4" type="video/mp4">
    </video>
</div>
'''
map.get_root().html.add_child(folium.Element(video_html))

Geocoder(position="topright", add_marker=False).add_to(map)

regions=["auvergne-rhone-alpes","bourgogne-franche-comte","bretagne","centre-val-de-loire","corse","grand-est","hauts-de-france","ile-de-france","normandie","nouvelle-aquitaine","occitanie","pays-de-la-loire","provence-alpes-cote-d-azur"]

groupe_regions = folium.FeatureGroup(name="1. Régions")
groupe_departements = folium.FeatureGroup(name="2. Départements", show=False)
groupe_commune=folium.FeatureGroup(name="3. Communes", show=False)


departements=["Paris","Vaucluse","Territoire-de-Belfort","Seine-Maritime","Hauts-de-Seine","Haut-Rhin","Gironde"]

stats_departements = []

for dep in departements:
        chemin_toits=f"C:/Users/spinalie/Documents/Evaluation_PV_toitures_France/data/processed/TEST/{dep}.gpkg"
        gdf=gpd.read_file(chemin_toits)
        
        surf_tot_globale=gdf['surf_tot_m2'].sum()
        somme_plate = gdf['surf_plate_m2'].sum()

        prod_kwh=gdf["prod_an_kwh"].sum()
        prod_twh = round(prod_kwh / 1e9, 3)

        stats_departements.append({
            "nom": dep,
            "production_estimee": prod_twh,
            "nombre_toitures": len(gdf),
            "prop_plat": (somme_plate / surf_tot_globale) * 100 if surf_tot_globale > 0 else 0,
            "prop_incl": 100 - ((somme_plate / surf_tot_globale) * 100) if surf_tot_globale > 0 else 0
        })
        del gdf

        df_stats = pd.DataFrame(stats_departements)


for region in regions:
    chemin="C:/Users/spinalie/Documents/Evaluation_PV_toitures_France/data/processed/contours/region/region-" + region + ".geojson"
    chemin_dep="C:/Users/spinalie/Documents/Evaluation_PV_toitures_France/data/processed/contours/departement/departements-" + region + ".geojson"
    chemin_com="C:/Users/spinalie/Documents/Evaluation_PV_toitures_France/data/processed/contours/communes/communes-" + region + ".geojson"
    folium.GeoJson(chemin, 
                   name=region.replace("-"," ").title()
                   ,zoom_on_click=True
                   ,style_function=lambda x: {"color": "#003CFF", "weight": 2, "fillOpacity": 0},
                    highlight_function=lambda x: {"fillColor": "#FBFF00", "fillOpacity": 0.4},
                   tooltip=folium.GeoJsonTooltip(fields=["nom"], aliases=["Région :"])
                   ).add_to(groupe_regions)

    gdf_contours_dep = gpd.read_file(chemin_dep)
    gdf_contours_dep = gdf_contours_dep.merge(df_stats, left_on="nom", right_on="nom", how="left")
    colonnes_stats = ["production_estimee", "nombre_toitures", "prop_plat", "prop_incl"]
    gdf_contours_dep[colonnes_stats] = gdf_contours_dep[colonnes_stats].fillna("Non calculé")
    folium.GeoJson(gdf_contours_dep,
                    name=region.replace("-"," ").title() + " (Départements)",
                    style_function=lambda x: {"color": "#00D7FD", "weight": 1.5, "fillOpacity": 0},
                    highlight_function=lambda x: {"fillColor": "#F0FC4C", "color": "#00BFFF", "weight": 2, "fillOpacity": 0.4},
                    popup=folium.GeoJsonPopup(
                        fields=["nom", "production_estimee", "nombre_toitures", "prop_plat", "prop_incl"], 
                        aliases=["Département :", "Production totale (TWh/an) :", "Nb de toitures :", "Toits plats (%) :", "Toits inclinés (%) :"],
                        style="font-family: Arial; padding: 10px; font-size: 14px; min-width: 220px;")
                    ).add_to(groupe_departements)
    
    folium.GeoJson(chemin_com, 
                   name=region.replace("-"," ").title()
                   ,zoom_on_click=True
                   ,style_function=lambda x: {"color": "#befffc", "weight": 1, "fillOpacity": 0},
                     highlight_function=lambda x: {"fillColor": "#FFFFFF", "color": "#006400", "weight": 1.5, "fillOpacity": 0.6},
                    tooltip=folium.GeoJsonTooltip(fields=["nom"], aliases=["Commune :"])
                   ).add_to(groupe_commune)




            
groupe_regions.add_to(map)
groupe_departements.add_to(map)
groupe_commune.add_to(map)



folium.LayerControl(position='topleft', collapsed=False).add_to(map)

map.save('carte.html')