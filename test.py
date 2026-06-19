import requests

def adresse_vers_coords(adresse: str):
    """Renvoie (lon, lat) pour une adresse donnee, ou None si rien trouve."""
    r = requests.get(
        "https://data.geopf.fr/geocodage/search",
        params={"q": adresse, "limit": 1}
    )
    lon, lat = r.json()["features"][0]["geometry"]["coordinates"]
    return lon, lat


def main():
    a = input("adresse :  ").strip()
    lon, lat= adresse_vers_coords(a)

    print(f"lon={lon}, lat={lat}")


if __name__ == "__main__":
    main()