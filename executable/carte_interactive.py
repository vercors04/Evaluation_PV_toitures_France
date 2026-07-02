import folium
import geopandas as gpd
import pandas as pd
from folium.plugins import Geocoder
import os 

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

css_zoom_dynamique = """
<style>

.leaflet-zoom-8 .leaflet-interactive[stroke="#FFFFFF"], .leaflet-zoom-9 .leaflet-interactive[stroke="#FFFFFF"],
.leaflet-zoom-10 .leaflet-interactive[stroke="#FFFFFF"], .leaflet-zoom-11 .leaflet-interactive[stroke="#FFFFFF"],
.leaflet-zoom-12 .leaflet-interactive[stroke="#FFFFFF"], .leaflet-zoom-13 .leaflet-interactive[stroke="#FFFFFF"],
.leaflet-zoom-8 .leaflet-interactive[stroke="#ffffff"], .leaflet-zoom-9 .leaflet-interactive[stroke="#ffffff"],
.leaflet-zoom-10 .leaflet-interactive[stroke="#ffffff"], .leaflet-zoom-11 .leaflet-interactive[stroke="#ffffff"],
.leaflet-zoom-12 .leaflet-interactive[stroke="#ffffff"], .leaflet-zoom-13 .leaflet-interactive[stroke="#ffffff"] {
    display: none !important;
}

.leaflet-zoom-1 .leaflet-interactive[stroke="#1A252C"], .leaflet-zoom-2 .leaflet-interactive[stroke="#1A252C"],
.leaflet-zoom-3 .leaflet-interactive[stroke="#1A252C"], .leaflet-zoom-4 .leaflet-interactive[stroke="#1A252C"],
.leaflet-zoom-5 .leaflet-interactive[stroke="#1A252C"], .leaflet-zoom-6 .leaflet-interactive[stroke="#1A252C"],
.leaflet-zoom-7 .leaflet-interactive[stroke="#1A252C"],
.leaflet-zoom-1 .leaflet-interactive[stroke="#1a252c"], .leaflet-zoom-2 .leaflet-interactive[stroke="#1a252c"],
.leaflet-zoom-3 .leaflet-interactive[stroke="#1a252c"], .leaflet-zoom-4 .leaflet-interactive[stroke="#1a252c"],
.leaflet-zoom-5 .leaflet-interactive[stroke="#1a252c"], .leaflet-zoom-6 .leaflet-interactive[stroke="#1a252c"],
.leaflet-zoom-7 .leaflet-interactive[stroke="#1a252c"] {
    display: none ;
}

.leaflet-zoom-1 .leaflet-interactive[stroke="#7F8C8D"], .leaflet-zoom-2 .leaflet-interactive[stroke="#7F8C8D"],
.leaflet-zoom-3 .leaflet-interactive[stroke="#7F8C8D"], .leaflet-zoom-4 .leaflet-interactive[stroke="#7F8C8D"],
.leaflet-zoom-5 .leaflet-interactive[stroke="#7F8C8D"], .leaflet-zoom-6 .leaflet-interactive[stroke="#7F8C8D"],
.leaflet-zoom-7 .leaflet-interactive[stroke="#7F8C8D"], .leaflet-zoom-8 .leaflet-interactive[stroke="#7F8C8D"],
.leaflet-zoom-9 .leaflet-interactive[stroke="#7F8C8D"], .leaflet-zoom-10 .leaflet-interactive[stroke="#7F8C8D"],
.leaflet-zoom-1 .leaflet-interactive[stroke="#7f8c8d"], .leaflet-zoom-2 .leaflet-interactive[stroke="#7f8c8d"],
.leaflet-zoom-3 .leaflet-interactive[stroke="#7f8c8d"], .leaflet-zoom-4 .leaflet-interactive[stroke="#7f8c8d"],
.leaflet-zoom-5 .leaflet-interactive[stroke="#7f8c8d"], .leaflet-zoom-6 .leaflet-interactive[stroke="#7f8c8d"],
.leaflet-zoom-7 .leaflet-interactive[stroke="#7f8c8d"], .leaflet-zoom-8 .leaflet-interactive[stroke="#7f8c8d"],
.leaflet-zoom-9 .leaflet-interactive[stroke="#7f8c8d"], .leaflet-zoom-10 .leaflet-interactive[stroke="#7f8c8d"] {
    display: none ;
}
</style>
"""

css_popup = """
<style>
.leaflet-popup-content-wrapper { background: #ffffff; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); padding: 0; overflow: hidden; }
.leaflet-popup-tip { background: #ffffff; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
.leaflet-popup-content { margin: 0 !important; width: 330px !important; }
.leaflet-popup-content table { width: 100%; border-collapse: collapse; font-family: 'Helvetica Neue', Arial, sans-serif; }
.leaflet-popup-content th, .leaflet-popup-content td { padding: 12px 15px; border-bottom: 1px solid #F0F3F4; }
.leaflet-popup-content tr:last-child th, .leaflet-popup-content tr:last-child td { border-bottom: none; }

.leaflet-popup-content th { font-size: 13px; font-weight: 600; text-align: left; width: 60%; }
.leaflet-popup-content td { font-size: 14px; font-weight: 900; text-align: right; }

.leaflet-popup-content tr:nth-child(1) { background: linear-gradient(135deg, #1A252C, #2C3E50); }
.leaflet-popup-content tr:nth-child(1) th { color: #E67E22; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
.leaflet-popup-content tr:nth-child(1) td { color: #FFFFFF; font-size: 16px; }

.leaflet-popup-content tr:nth-child(2) { background-color: #F4FCF7; }
.leaflet-popup-content tr:nth-child(2) th, .leaflet-popup-content tr:nth-child(2) td { color: #27AE60; }

.leaflet-popup-content tr:nth-child(3) { background-color: #F0F8FF; }
.leaflet-popup-content tr:nth-child(3) th, .leaflet-popup-content tr:nth-child(3) td { color: #2980B9; }

.leaflet-popup-content tr:nth-child(4) { background-color: #FAF4FC; }
.leaflet-popup-content tr:nth-child(4) th, .leaflet-popup-content tr:nth-child(4) td { color: #8E44AD; }

.leaflet-popup-content tr:nth-child(5) { background-color: #FFFDF4; }
.leaflet-popup-content tr:nth-child(5) th, .leaflet-popup-content tr:nth-child(5) td { color: #D35400; }
</style>
"""

js_moteur_zoom = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    let leafletMap = null;
    for (let key in window) {
        if (key.startsWith("map_") && window[key].getZoom) {
            leafletMap = window[key];
            break;
        }
    }
    
    if (leafletMap) {
        let container = leafletMap.getContainer();
        function updateZoomClass() {
            let zoom = leafletMap.getZoom();
            container.className = container.className.split(' ').filter(c => !c.startsWith('leaflet-zoom-')).join(' ');
            container.classList.add('leaflet-zoom-' + zoom);
        }
        
        leafletMap.on('zoomend', updateZoomClass);
        updateZoomClass();
    }
});
</script>
"""
map.get_root().html.add_child(folium.Element(js_moteur_zoom))
map.get_root().html.add_child(folium.Element(css_zoom_dynamique))
map.get_root().html.add_child(folium.Element(css_zoom_dynamique))
map.get_root().html.add_child(folium.Element(css_popup))
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

logo_html = '''
<div style="position: fixed; 
            bottom: 25px; right: 25px; 
            z-index: 9999; 
            pointer-events: none;"> <img src="data/assets/logo_soleil.png" 
         alt="Logo Projet" 
         style="height: 60px; width: auto; 
                filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.2));">
</div>
'''
map.get_root().html.add_child(folium.Element(logo_html))

Geocoder(position="topright", zoom=13,add_marker=True).add_to(map)

regions=["auvergne-rhone-alpes","bourgogne-franche-comte","bretagne","centre-val-de-loire","corse","grand-est","hauts-de-france","ile-de-france","normandie","nouvelle-aquitaine","occitanie","pays-de-la-loire","provence-alpes-cote-d-azur"]

groupe_regions = folium.FeatureGroup(name="1. Régions")
groupe_departements = folium.FeatureGroup(name="2. Départements")
groupe_commune=folium.FeatureGroup(name="3. Communes")

gdfs_communes = []
for reg in regions:
    chemin_com = f"data/contours/communes/communes-{reg}.geojson"
    if os.path.exists(chemin_com):
        gdf_c = gpd.read_file(chemin_com)[['code', 'geometry']]
        gdf_c['code_region_id'] = reg.replace("-"," ").title()
        gdfs_communes.append(gdf_c)
gdf_toutes_communes = gpd.GeoDataFrame(pd.concat(gdfs_communes, ignore_index=True), crs="EPSG:4326")

liste_gpkg=os.listdir("data/processed/gpkg")
noms_propres = sorted([dep.replace(".gpkg", "").replace("-", " ") for dep in liste_gpkg])
lignes_html = "".join([f'<li style="margin-bottom: 4px;"><span style="color:#E67E22; margin-right:6px; font-size:10px;">▶</span>{nom}</li>' for nom in noms_propres])

liste_bas_gauche = f'''
<div style="position: fixed; bottom: 25px; left: 25px; z-index: 9999; 
            background-color: rgba(255, 255, 255, 0.95); 
            padding: 15px 20px; border-radius: 12px; 
            box-shadow: 0 4px 16px rgba(0,0,0,0.2); border: 1px solid rgba(0,0,0,0.08);
            font-family: 'Helvetica Neue', Arial, sans-serif;
            max-height: 280px; overflow-y: auto; width: 240px;">
    <div style="font-size: 11px; color: #7F8C8D; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">
        Base de données
    </div>
    <div style="font-size: 14px; color: #1A252C; margin-bottom: 12px; font-weight: bold; border-bottom: 1px solid #EEE; padding-bottom: 6px;">
        Secteurs traités ({len(noms_propres)})
    </div>
    <ul style="list-style-type: none; padding-left: 0; margin: 0; font-size: 13px; color: #2C3E50;">
        {lignes_html}
    </ul>
</div>
'''
map.get_root().html.add_child(folium.Element(liste_bas_gauche))


stats_dep = []
stats_com_list = []
deps_complets = set()

for dep in liste_gpkg:
        chemin_toits=f"data/processed/gpkg/{dep}"
        gdf=gpd.read_file(chemin_toits)
        
        surf_tot_globale=gdf['surf_tot_m2'].sum()
        somme_plate = gdf['surf_plate_m2'].sum()

        prod_kwh=gdf["prod_an_kwh"].sum()
        prod_twh = round(prod_kwh / 1e9, 3)

        stats_dep.append({
            "nom": dep,
            "production_estimee": prod_twh,
            "nombre_toitures": len(gdf),
            "prop_plat": (somme_plate / surf_tot_globale) * 100 if surf_tot_globale > 0 else 0,
            "prop_incl": 100 - ((somme_plate / surf_tot_globale) * 100) if surf_tot_globale > 0 else 0
        })
        
        
        gdf_points = gpd.GeoDataFrame(gdf[['surf_tot_m2', 'surf_plate_m2', 'prod_an_kwh']], geometry=gdf.centroid, crs=gdf.crs)
    
        gdf_points = gdf_points.to_crs("EPSG:4326")
        gdf_croise = gpd.sjoin(gdf_points, gdf_toutes_communes, how="inner", predicate="within")
        counts_commune = gdf_croise['code'].value_counts(normalize=True)
        commune_majoritaire = counts_commune.idxmax()
        proportion_max = counts_commune.max()
        
        if proportion_max > 0.70:
            gdf_croise = gdf_croise[gdf_croise['code'] == commune_majoritaire]
        else:
            gdf_croise['code_dep_temp'] = gdf_croise['code'].astype(str).str[:2]
            dep_majoritaire = gdf_croise['code_dep_temp'].mode()[0]
            gdf_croise = gdf_croise[gdf_croise['code_dep_temp'] == dep_majoritaire]
            deps_complets.add(dep_majoritaire)

        group = gdf_croise.groupby(['code','code_region_id']).agg(
        surf_tot_globale=('surf_tot_m2', 'sum'),
        somme_plate=('surf_plate_m2', 'sum'),
        prod_kwh=('prod_an_kwh', 'sum'),
        nombre_toitures=('code', 'size') 
        ).reset_index()

        stats_com_list.append(group)
        
        del gdf, gdf_points, gdf_croise

df_stats_com_raw = pd.concat(stats_com_list, ignore_index=True)
df_stats_com = df_stats_com_raw.groupby(['code', 'code_region_id']).agg(
    surf_tot_globale=('surf_tot_globale', 'sum'),
    somme_plate=('somme_plate', 'sum'),
    prod_kwh=('prod_kwh', 'sum'),
    nombre_toitures=('nombre_toitures', 'sum')
).reset_index()

df_stats_com['production_estimee'] = (df_stats_com['prod_kwh'] / 1e6).round(5)
df_stats_com['prop_plat'] = (df_stats_com['somme_plate'] / df_stats_com['surf_tot_globale']) * 100
df_stats_com['prop_plat'] = df_stats_com['prop_plat'].fillna(0)
df_stats_com['prop_incl'] = 100 - df_stats_com['prop_plat']

df_stats_com['code_dep'] = df_stats_com['code'].astype(str).str[:2]
df_stats_com_pour_dep = df_stats_com[df_stats_com['code_dep'].isin(deps_complets)]

df_stats_dep = df_stats_com_pour_dep.groupby(['code_dep', 'code_region_id']).agg(
    surf_tot_globale=('surf_tot_globale', 'sum'),
    somme_plate=('somme_plate', 'sum'),
    prod_kwh=('prod_kwh', 'sum'),
    nombre_toitures=('nombre_toitures', 'sum')
).reset_index()

df_stats_dep['production_estimee'] = (df_stats_dep['prod_kwh'] / 1e9).round(3)
df_stats_dep['prop_plat'] = (df_stats_dep['somme_plate'] / df_stats_dep['surf_tot_globale']) * 100
df_stats_dep['prop_plat'] = df_stats_dep['prop_plat'].fillna(0)
df_stats_dep['prop_incl'] = 100 - df_stats_dep['prop_plat']

df_stats_reg = df_stats_dep.groupby('code_region_id').agg(
    surf_tot_globale=('surf_tot_globale', 'sum'),
    somme_plate=('somme_plate', 'sum'),
    prod_kwh=('prod_kwh', 'sum'),
    nombre_toitures=('nombre_toitures', 'sum')
).reset_index()

df_stats_reg['production_estimee'] = (df_stats_reg['prod_kwh'] / 1e9).round(3)
df_stats_reg['prop_plat'] = (df_stats_reg['somme_plate'] / df_stats_reg['surf_tot_globale']) * 100
df_stats_reg['prop_plat'] = df_stats_reg['prop_plat'].fillna(0)
df_stats_reg['prop_incl'] = 100 - df_stats_reg['prop_plat']
colonnes_stats = ["production_estimee", "nombre_toitures", "prop_plat", "prop_incl"]
for region in regions:
    chemin="data/contours/region/region-" + region + ".geojson"
    chemin_dep="data/contours/departement/departements-" + region + ".geojson"
    chemin_com="data/contours/communes/communes-" + region + ".geojson"

    nom_propre_region = region.replace("-"," ").title()

    gdf_contours_reg = gpd.read_file(chemin)
    gdf_contours_reg['region_key'] = nom_propre_region
    gdf_contours_reg = gdf_contours_reg.merge(df_stats_reg, left_on="region_key", right_on="code_region_id", how="left")
    gdf_contours_reg[colonnes_stats] = gdf_contours_reg[colonnes_stats].fillna("Non calculé")
    folium.GeoJson(gdf_contours_reg, 
                   name=region.replace("-"," ").title()
                   ,zoom_on_click=True
                   ,style_function=lambda x: {"color": "#FFFFFF", "weight": 2, "fillOpacity": 0},
                   highlight_function=lambda x: {"fillColor": "#1A252C", "fillOpacity": 0.2},
                   tooltip=folium.GeoJsonTooltip(fields=["nom"], aliases=["Région :"]),
                   popup=folium.GeoJsonPopup(
                        fields=["nom", "production_estimee", "nombre_toitures", "prop_plat", "prop_incl"], 
                        aliases=["Région :", "Production totale (TWh/an) :", "Nb de toitures :", "Toits plats (%) :", "Toits inclinés (%) :"],
                       )
                   ).add_to(groupe_regions)

    gdf_contours_dep = gpd.read_file(chemin_dep)
    gdf_contours_dep['code'] = gdf_contours_dep['code'].astype(str)
    gdf_contours_dep = gdf_contours_dep.merge(df_stats_dep, left_on="code", right_on="code_dep", how="left")
    gdf_contours_dep[colonnes_stats] = gdf_contours_dep[colonnes_stats].fillna("Non calculé")
    gdf_contours_dep[colonnes_stats] = gdf_contours_dep[colonnes_stats].fillna("Non calculé")
    folium.GeoJson(gdf_contours_dep,
                    name=region.replace("-"," ").title() + " (Départements)",
                    style_function=lambda x: {"color": "#1A252C", "weight": 1.5, "fillOpacity": 0.1, "fillColor": "#2C3E50"},
                    highlight_function=lambda x: {"fillColor": "#FFFFFF", "color": "#FFFFFF", "weight": 2.5, "fillOpacity": 0.3},
                    popup=folium.GeoJsonPopup(
                        fields=["nom", "production_estimee", "nombre_toitures", "prop_plat", "prop_incl"], 
                        aliases=["Département :", "Production totale (TWh/an) :", "Nb de toitures :", "Toits plats (%) :", "Toits inclinés (%) :"],
                        )
                    ).add_to(groupe_departements)
    
    gdf_communes = gpd.read_file(chemin_com)
    gdf_communes['geometry'] = gdf_communes['geometry'].simplify(tolerance=0.001, preserve_topology=True)
    gdf_communes = gdf_communes.merge(df_stats_com, on="code", how="left")
    
    for col in colonnes_stats:
            if col not in gdf_communes.columns:
                gdf_communes[col] = "Non calculé"
    gdf_communes[colonnes_stats] = gdf_communes[colonnes_stats].fillna("Non calculé")
    folium.GeoJson(gdf_communes, 
                   name=region.replace("-"," ").title()+ " (Commune)"
                   ,zoom_on_click=True
                   ,style_function=lambda x: {"color": "#7F8C8D", "weight": 1.2, "fillOpacity": 0},
                   highlight_function=lambda x: {"fillColor": "#FFFFFF", "color": "#1A252C", "weight": 1.5, "fillOpacity": 0.4},
                   popup=folium.GeoJsonPopup(
                        fields=["nom", "production_estimee", "nombre_toitures", "prop_plat", "prop_incl"], 
                        aliases=["Commune :", "Production totale (GWh/an) :", "Nb de toitures :", "Toits plats (%) :", "Toits inclinés (%) :"],
                        ),
                    tooltip=folium.GeoJsonTooltip(fields=["nom"], aliases=["Commune :"])
                   ).add_to(groupe_commune)

groupe_regions.add_to(map)
groupe_departements.add_to(map)
groupe_commune.add_to(map)

folium.LayerControl(position='topleft', collapsed=False).add_to(map)

map.save('carte.html')