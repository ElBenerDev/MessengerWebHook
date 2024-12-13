import requests

def extract_filters(user_message):
    filters = {
        "price_from": 0,
        "price_to": 1000000,
        "operation_types": [],
        "property_types": [],
        "currency": "USD",
        "location": None,
    }

    if "alquiler" in user_message.lower():
        filters["operation_types"] = [2]
    elif "comprar" in user_message.lower() or "venta" in user_message.lower():
        filters["operation_types"] = [1]
    elif "alquiler temporal" in user_message.lower():
        filters["operation_types"] = [3]

    if "menos de" in user_message.lower():
        try:
            price_to = int(user_message.split("menos de")[1].split()[0].replace(",", "").replace(".", ""))
            filters["price_to"] = price_to
        except ValueError:
            pass

    if "más de" in user_message.lower():
        try:
            price_from = int(user_message.split("más de")[1].split()[0].replace(",", "").replace(".", ""))
            filters["price_from"] = price_from
        except ValueError:
            pass

    if "departamento" in user_message.lower():
        filters["property_types"].append(2)
    if "casa" in user_message.lower():
        filters["property_types"].append(3)
    if "oficina" in user_message.lower():
        filters["property_types"].append(5)

    if "en" in user_message.lower():
        try:
            location = user_message.split("en")[1].split()[0]
            filters["location"] = location
        except IndexError:
            pass

    return filters

def search_properties(filters):
    tokko_url = "https://www.tokkobroker.com/api/v1/property/search?key=34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        response = requests.post(tokko_url, json=filters)
        response.raise_for_status()

        properties = response.json()
        results = []

        for property in properties.get('objects', []):
            results.append({
                'title': property.get('title', 'Sin título'),
                'price': property.get('price', 'No especificado'),
                'location': property.get('location', {}).get('address', 'Ubicación no disponible'),
                'description': property.get('description', 'Sin descripción'),
            })

        return results

    except requests.exceptions.RequestException as e:
        print(f"Error al conectarse a la API de Tokko: {e}")
        return None