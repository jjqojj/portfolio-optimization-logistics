import pandas as pd
import random
import os

class BogotaDataGenerator:
    """
    Clase encargada de simular la demanda logistica y la flota de vehiculos,
    garantizando consistencia geometrica real por localidades de Bogota.
    """
    def __init__(self, num_customers: int = 50, output_dir: str = "data/raw"):
        self.num_customers = num_customers
        self.output_dir = output_dir
        
        # ENCAPSULAMIENTO: Poligonos bounding-box reales de Bogota por localidad
        # Formato: (Lat_Min, Lat_Max, Lon_Min, Lon_Max)
        self.__boundaries = {
            "Usaquen":   (4.7000, 4.7500, -74.0500, -74.0100),
            "Suba":      (4.7000, 4.7500, -74.1300, -74.0600),
            "Chapinero": (4.6200, 4.6999, -74.0700, -74.0300),
            "Fontibon":  (4.6500, 4.6999, -74.1400, -74.0800),
            "Kennedy":   (4.6000, 4.6499, -74.1600, -74.1100),
            "Bosa":      (4.5900, 4.6300, -74.1900, -74.1700)
        }
        
        os.makedirs(self.output_dir, exist_ok=True)

    def __resolve_zone(self, lat: float, lon: float) -> str:
        """
        Metodo Privado (Point-in-Polygon Heuristic): 
        Evalua a que poligono pertenece la coordenada generada.
        """
        for zone, bounds in self.__boundaries.items():
            lat_min, lat_max, lon_min, lon_max = bounds
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return zone
        return "Unknown_Zone"

    def generate_customers(self) -> pd.DataFrame:
        """Genera clientes distribuidos dentro del espacio real de Bogota."""
        customers_list = []
        
        # Para generar coordenadas validas, tomamos los limites globales de los poligonos
        global_lat_min = min(b[0] for b in self.__boundaries.values())
        global_lat_max = max(b[1] for b in self.__boundaries.values())
        global_lon_min = min(b[2] for b in self.__boundaries.values())
        global_lon_max = max(b[3] for b in self.__boundaries.values())
        
        generated = 0
        while generated < self.num_customers:
            lat = round(random.uniform(global_lat_min, global_lat_max), 4)
            lon = round(random.uniform(global_lon_min, global_lon_max), 4)
            
            # Validacion geometrica
            zone = self.__resolve_zone(lat, lon)
            
            # Si la coordenada no cae en ninguna de nuestras localidades definidas, se descarta
            if zone == "Unknown_Zone":
                continue
                
            generated += 1
            customers_list.append({
                "customer_id": generated,
                "customer_name": f"Retail_Store_{generated}",
                "location_latitude": lat,
                "location_longitude": lon,
                "zone_bogota": zone
            })
            
        return pd.DataFrame(customers_list)

    def generate_vehicles(self) -> pd.DataFrame:
        """Define la flota de camiones asignada al CEDI Fontibon."""
        fleet = []
        plates = ["SXM543", "TTW987", "KLO123", "ZXC456", "VBN789"]
        
        for i, plate in enumerate(plates, start=1):
            fleet.append({
                "vehicle_id": i,
                "plate_number": plate,
                "max_weight_kg": 3500.0,
                "max_volume_m3": 18.0
            })
        return pd.DataFrame(fleet)

    def run_pipeline(self):
        """Orquesta la generacion y exporta los archivos inmutables."""
        print("[INFO] Initiating georeferenced data generation pipeline...")
        
        df_customers = self.generate_customers()
        df_vehicles = self.generate_vehicles()
        
        customers_path = os.path.join(self.output_dir, "dim_customers.csv")
        vehicles_path = os.path.join(self.output_dir, "dim_vehicles.csv")
        
        df_customers.to_csv(customers_path, index=False)
        df_vehicles.to_csv(vehicles_path, index=False)
        
        print(f"[SUCCESS] Spatial-consistent datasets exported to: {self.output_dir}")

if __name__ == "__main__":
    generator = BogotaDataGenerator(num_customers=60)
    generator.run_pipeline()