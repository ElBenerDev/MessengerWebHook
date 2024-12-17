import requests
import logging
import sys
import os
from datetime import datetime
from flask import Flask, request, jsonify

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class TokkoManager:
    def __init__(self):
        # Obtener API key desde variable de entorno
        self.api_key = os.getenv('TOKKO_API_KEY', "34430fc661d5b961de6fd53a9382f7a232de3ef0")
        self.api_url = "https://www.tokkobroker.com/api/v1/property/"

    def get_active_properties(self, properties):
        """Filtrar propiedades activas"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        active_properties = [
            prop for prop in properties 
            if prop.get('status') == 2 and 
               (prop.get('deleted_at') is None or prop.get('deleted_at') > current_date)
        ]
        return active_properties

    def search_properties(self, **kwargs):
        try:
            # Preparar parámetros base
            params = {
                "key": self.api_key,
                "limit": kwargs.get('limit', 20),
                "order_by": kwargs.get('order_by', '-publication_date')
            }

            # Agregar todos los parámetros proporcionados
            for key, value in kwargs.items():
                if key not in ['limit', 'order_by', 'key']:
                    params[key] = value

            # Realizar la solicitud a la API
            response = requests.get(self.api_url, params=params)

            if response.status_code != 200:
                return {
                    "error": "No se pudo conectar con el sistema de búsqueda",
                    "status_code": response.status_code
                }

            data = response.json()

            # Verificar si hay propiedades
            properties = data.get('objects', [])
            if not properties:
                return {
                    "message": "No se encontraron propiedades",
                    "total": 0,
                    "properties": []
                }

            # Filtrar propiedades activas
            active_properties = self.get_active_properties(properties)

            # Formatear propiedades
            formatted_properties = []
            for prop in active_properties:
                # Información básica de la propiedad
                property_details = {
                    "id": prop.get('id'),
                    "title": prop.get('publication_title', 'Propiedad disponible'),
                    "address": prop.get('address', 'Dirección no disponible'),
                    "type": prop.get('type', {}).get('name'),
                    "status": prop.get('status'),
                    "publication_date": prop.get('publication_date'),
                    "public_url": prop.get('public_url')  # Agregar URL pública
                }

                # Agregar operaciones (precios)
                operations = []
                for op in prop.get('operations', []):
                    operation_info = {
                        "operation_type": op.get('operation_type'),
                        "prices": [
                            {
                                "currency": price.get('currency'),
                                "price": price.get('price'),
                                "price_type": price.get('price_type')
                            } for price in op.get('prices', [])
                        ]
                    }
                    operations.append(operation_info)
                property_details['operations'] = operations

                # Características adicionales
                property_details.update({
                    "surface": {
                        "total": prop.get('total_surface'),
                        "covered": prop.get('covered_surface')
                    },
                    "rooms": {
                        "total": prop.get('room_amount'),
                        "bedrooms": prop.get('bedroom_amount'),
                        "bathrooms": prop.get('bathroom_amount')
                    },
                    "location": prop.get('location', {}).get('full_location'),
                    "features": [feature.get('name') for feature in prop.get('features', [])],
                    "photos": [photo.get('image') for photo in prop.get('photos', [])],
                })

                formatted_properties.append(property_details)

            return {
                "total": len(active_properties),
                "properties": formatted_properties
            }

        except Exception as e:
            logging.error(f"Error en búsqueda: {str(e)}")
            return {
                "error": "Ocurrió un error al buscar propiedades",
                "details": str(e)
            }

# Configurar Flask
app = Flask(__name__)

@app.route('/search', methods=['GET', 'POST'])
def search_properties():
    # Obtener parámetros de búsqueda
    if request.method == 'POST':
        search_params = request.json or request.form.to_dict()
    else:
        search_params = request.args.to_dict()

    try:
        # Convertir valores numéricos
        for key in ['limit', 'page', 'room_amount', 'bedroom_amount', 'bathroom_amount']:
            if key in search_params:
                try:
                    search_params[key] = int(search_params[key])
                except ValueError:
                    return jsonify({
                        "error": f"El parámetro {key} debe ser un número entero",
                        "status": "bad_request"
                    }), 400

        # Realizar búsqueda
        tokko = TokkoManager()
        result = tokko.search_properties(**search_params)

        return jsonify(result)

    except Exception as e:
        logging.error(f"Error en búsqueda: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "details": str(e)
        }), 500

# Función de búsqueda directa
def search_properties_func(**kwargs):
    """Función principal que busca propiedades"""
    try:
        tokko = TokkoManager()
        return tokko.search_properties(**kwargs)
    except Exception as e:
        logging.error(f"❌ Error en search_properties: {str(e)}")
        return {"error": "Ocurrió un error al buscar propiedades"}

if __name__ == "__main__":
    # Ejemplo de uso directo
    result = search_properties_func(
        operation_type="Sale", 
        property_type="Apartment", 
        location="Villa Ballester"
    )
    print(result)

    # Iniciar servidor Flask
    app.run(debug=True, port=5000)