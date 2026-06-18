from statistics import mean
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def main():
    #['cleabs', 'nature', 'usage_1', 'hauteur', 'nombre_d_etages', 'irr_an_kwh', 'surf_inclinee_m2', 'surf_plate_m2', 'pente_moy_incl', 'nb_pixels', 'surf_N_m2_incl', 'surf_NE_m2_incl', 'surf_E_m2_incl', 'surf_SE_m2_incl', 'surf_S_m2_incl', 'surf_SO_m2_incl', 'surf_O_m2_incl_incl', 'surf_NO_m2_incl', 'surf_tot_m2', 'irr_an_kwh_m2', 'puissance_kwc', 'prod_an_kwh', 'geometry']
    gdf=gpd.read_file("05_Stats/stats_totales_dalles_didier.gpkg")

    with open("05_Stats/bilan_statistiques.md", "w", encoding="utf-8") as f:
        valeurs_surfaces = []
        labels_orientations = []
        for orientation in ['N','NE','E','SE','S','SO','O','NO']:
            surf_tot_orientee=gdf[f'surf_{orientation}_m2'].sum()
            surf_tot_globale=gdf['surf_tot_m2'].sum()
            ratio=(surf_tot_orientee/surf_tot_globale)*100
            print(f"Pourcentage de surface orientée {orientation}: {ratio:.2f}%", file=f)

            valeurs_surfaces.append(surf_tot_orientee)
            labels_orientations.append(orientation)

        somme_plate = gdf['surf_plate_m2'].sum()
        ratio_plat = (somme_plate / surf_tot_globale) * 100

        valeurs_surfaces.append(somme_plate)
        labels_orientations.append('Plats')

        plt.figure(figsize=(9, 9))
        couleurs = [
            '#4A90E2',
            '#50E3C2',
            '#B8E986',
            '#F8E71C',
            '#F5A623',
            '#D0021B',
            '#BD10E0',
            '#9013FE',
            "#AAAAAA"
        ]
        plt.pie(valeurs_surfaces, labels=labels_orientations, colors=couleurs,autopct='%1.1f%%', startangle=90)
        plt.title('Proportion de chaque orientation pour les toits inclinés', fontweight='bold')

        plt.savefig("05_Stats/toutes_orientations_proportions.png",dpi=300, bbox_inches='tight')
        plt.close()
        
        print("[Représentation graphique](toutes_orientations_proportions.png)", file=f)

        print("\n================================================================", file=f)

        plt.figure(figsize=(2, 2))
        couleurs = [
            "#5FFFF2",
            "#FF0000"
        ]
        somme_inc=gdf['surf_inclinee_m2'].sum()
        somme_plate=gdf['surf_plate_m2'].sum()

        labels_surfaces=["Inclinées","Plates"]
        valeurs_surfaces=[]
        valeurs_surfaces.append(somme_inc)
        valeurs_surfaces.append(somme_plate)

        ratio_inc=(somme_inc/gdf['surf_tot_m2'].sum())*100
        ratio_plat=(somme_plate/gdf['surf_tot_m2'].sum())*100

        plt.pie(valeurs_surfaces, labels=labels_surfaces, colors=couleurs,autopct='%1.1f%%', startangle=90)
        plt.title('Proportion toitures inclinées et plates', fontweight='bold')

        plt.savefig("05_Stats/inclinees_plates.png",dpi=300, bbox_inches='tight')
        plt.close()
        

        print(f'Surface totale des toitures inclinées: {somme_inc:.2f} m2', file=f)
        print(f'Surface totale des toitures plates: {somme_plate:.2f} m2', file=f)

        print(f'Pourcentage de toitures inclinées: {ratio_inc:.2f}%', file=f)
        print(f'Pourcentage de toitures plats: {ratio_plat:.2f}%', file=f)

        print("[Représentation graphique](inclinees_plates.png)", file=f)
        
        print("\n================================================================", file=f)
        
        
        puissance_totale_kwc = gdf['puissance_kwc'].sum()
        production_totale_kwh = gdf['prod_an_kwh'].sum()
        
        puissance_moyenne_kwc = gdf['puissance_kwc'].mean()
        production_moyenne_kwh = gdf['prod_an_kwh'].mean()
        
        print(f"Nombre total de bâtiments : {len(gdf)}", file=f)
        print(f"Puissance totale installable : {puissance_totale_kwc:.1f} kWc", file=f)
        print(f"Production annuelle totale attendue : {production_totale_kwh:.0f} kWh/an", file=f)
        
        print(f"Puissance moyenne par bâtiment : {puissance_moyenne_kwc:.1f} kWc", file=f)
        print(f"Production moyenne par bâtiment : {production_moyenne_kwh:.0f} kWh/an", file=f)

        plt.figure()
        barres=plt.hist(gdf[gdf['puissance_kwc'] < 100]['puissance_kwc'], bins=10, edgecolor='black')[2]
        plt.bar_label(barres)
        plt.title('Distribution des puissances (< 100 kWc)')
        plt.xlabel('Puissance (kWc)')
        plt.ylabel('Nombre de surfaces')
        plt.xticks(range(0, 101, 10))
        plt.savefig("05_Stats/histogramme_puissance.png")
        plt.close()
        
        print("[Histogramme](histogramme_puissance.png)", file=f)
        print("\nMETHODE 1================================================================", file=f)


        orientations=['surf_N_m2_incl','surf_NE_m2_incl','surf_E_m2_incl','surf_SE_m2_incl','surf_S_m2_incl','surf_SO_m2_incl','surf_O_m2_incl_incl','surf_NO_m2_incl']

        orientation_principale=gdf[orientations].idxmax(axis=1)
        
        liste_toits_sud=[]
        liste_toits_nord=[]
        liste_toits_E_O=[]
        for i, orientation in orientation_principale.items():
            if orientation in ['surf_SE_m2_incl', 'surf_S_m2_incl', 'surf_SO_m2_incl']:
                liste_toits_sud.append(i) 
            elif orientation in ['surf_N_m2_incl', 'surf_NE_m2_incl', 'surf_NO_m2_incl']:
                liste_toits_nord.append(i) 
            else:
                liste_toits_E_O.append(i)

        pte_sud = gdf.loc[liste_toits_sud, 'pente_moy_incl'].mean()
        pte_nord = gdf.loc[liste_toits_nord, 'pente_moy_incl'].mean()
        pte_E_O = gdf.loc[liste_toits_E_O, 'pente_moy_incl'].mean()

        puissance_sud = gdf.loc[liste_toits_sud, 'puissance_kwc'].sum()
        puissance_nord = gdf.loc[liste_toits_nord, 'puissance_kwc'].sum()
        puissance_E_O = gdf.loc[liste_toits_E_O, 'puissance_kwc'].sum()

        production_sud = gdf.loc[liste_toits_sud, 'prod_an_kwh'].sum()
        production_nord = gdf.loc[liste_toits_nord, 'prod_an_kwh'].sum()
        production_E_O = gdf.loc[liste_toits_E_O, 'prod_an_kwh'].sum()

        irr_sud = gdf.loc[liste_toits_sud, 'irr_an_kwh_m2'].mean()
        irr_nord = gdf.loc[liste_toits_nord, 'irr_an_kwh_m2'].mean()
        irr_E_O = gdf.loc[liste_toits_E_O, 'irr_an_kwh_m2'].mean()

        print(f"Groupe SUD       : {len(liste_toits_sud)} toits | Pente moyenne: {pte_sud:4.1f}° | Puissance : {puissance_sud:7,.1f} kWc | Prod : {production_sud:10,.0f} kWh/an | Irradiation moyenne: {irr_sud:6.0f} kWh/m2" , file=f)
        print(f"Groupe EST/OUEST : {len(liste_toits_E_O):3} toits | Pente moyenne: {pte_E_O:4.1f}° | Puissance : {puissance_E_O:7,.1f} kWc | Prod : {production_E_O:10,.0f} kWh/an | Irradiation moyenne: {irr_E_O:6.0f} kWh/m2", file=f)
        print(f"Groupe NORD      : {len(liste_toits_nord)} toits | Pente moyenne: {pte_nord:4.1f}° | Puissance : {puissance_nord:7,.1f} kWc | Prod : {production_nord:10,.0f} kWh/an | Irradiation moyenne: {irr_nord:6.0f} kWh/m2", file=f)

        plt.figure(figsize=(8, 5))
        groupes = ['SUD', 'EST / OUEST', 'NORD']
        productions = [production_sud, production_E_O, production_nord]
        couleurs_barres = ['#F5A623', '#4A90E2', '#9013FE']

        barres=plt.bar(groupes, productions, color=couleurs_barres, edgecolor='black', width=0.6)
        plt.title('Production annuelle attendue par groupe d\'orientation avec la méthode 1', fontweight='bold', pad=15)
        plt.ylabel('Production (kWh/an)')
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.ticklabel_format(style='plain', axis='y')
        production_propres = [f"{v:,.0f}".replace(',', ' ') for v in productions]
        plt.bar_label(barres, labels=production_propres, padding=3, fontweight='bold')
        plt.savefig("05_Stats/production_par_orientation.png", dpi=300, bbox_inches='tight')
        plt.close()
        print("[Représentation graphique de la production](production_par_orientation.png)", file=f)

        print("\nMETHODE 2================================================================", file=f)
        surface_sud = gdf['surf_S_m2_incl'] + gdf['surf_SE_m2_incl'] + gdf['surf_SO_m2_incl']
        surface_nord = gdf['surf_N_m2_incl'] + gdf['surf_NE_m2_incl'] + gdf['surf_NO_m2_incl']
        surface_est_ouest = gdf['surf_E_m2_incl'] + gdf['surf_O_m2_incl']

        seuil = gdf['surf_tot_m2'] * 0.49

        gdf_sud = gdf[surface_sud > seuil]
        gdf_nord = gdf[surface_nord > seuil]
        gdf_est_ouest = gdf[surface_est_ouest > seuil]

        if len(gdf_sud) > 0:
            prod_sud = gdf_sud['prod_an_kwh'].sum()
            puiss_sud = gdf_sud['puissance_kwc'].sum()
            pente_sud = gdf_sud['pente_moy_incl'].mean()
            irr_m2_sud = gdf_sud['irr_an_kwh_m2'].mean()
            print(f"Groupe SUD        : {len(gdf_sud)} bâtiments | Pente moyenne: {pente_sud:4.1f}° | Puiss : {puiss_sud:7,.1f} kWc | Prod : {prod_sud:10,.0f} kWh/an | Irradiation moyenne: {irr_m2_sud:6.0f} kWh/m2", file=f)

        if len(gdf_est_ouest) > 0:
            prod_eo = gdf_est_ouest['prod_an_kwh'].sum()
            puiss_eo = gdf_est_ouest['puissance_kwc'].sum()
            pente_eo = gdf_est_ouest['pente_moy_incl'].mean()
            irr_m2_eo = gdf_est_ouest['irr_an_kwh_m2'].mean()
            print(f"Groupe EST/OUEST  : {len(gdf_est_ouest)} bâtiments | Pente moyenne: {pente_eo:4.1f}° | Puiss : {puiss_eo:7,.1f} kWc | Prod : {prod_eo:10,.0f} kWh/an | Irradiation moyenne: {irr_m2_eo:6.0f} kWh/m2", file=f)

        if len(gdf_nord) > 0:
            prod_nord = gdf_nord['prod_an_kwh'].sum()
            puiss_nord = gdf_nord['puissance_kwc'].sum()
            pente_nord = gdf_nord['pente_moy_incl'].mean()
            irr_m2_nord = gdf_nord['irr_an_kwh_m2'].mean()
            print(f"Groupe NORD       : {len(gdf_nord)} bâtiments | Pente moyenne: {pente_nord:4.1f}° | Puiss : {puiss_nord:7,.1f} kWc | Prod : {prod_nord:10,.0f} kWh/an | Irradiation moyenne: {irr_m2_nord:6.0f} kWh/m2", file=f)

if __name__ == "__main__":
    main()