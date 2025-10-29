"use client";

import { useEffect, useMemo, useRef } from "react";
import mapboxgl from "mapbox-gl";

type Restaurant = {
  id: number;
  nom: string;
  latitude: number | null;
  longitude: number | null;
  rating: number | null;
  website: string | null;
};

type Props = {
  restaurants: Restaurant[];
  selectedId?: number | null;
};

function RestaurantMap(props: Props) {
  const { restaurants = [], selectedId = null } = (props ?? {}) as Partial<Props>;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const idToCoordRef = useRef<Map<number, [number, number]>>(new globalThis.Map());
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

  const features = useMemo(() => {
    return restaurants
      .filter((r) => r.latitude !== null && r.longitude !== null)
      .map((r) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [Number(r.longitude), Number(r.latitude)],
        },
        properties: {
          id: r.id,
          nom: r.nom,
          rating: r.rating,
          website: r.website,
        },
      }));
  }, [restaurants]);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!token) return;

    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: features.length
        ? (features[0].geometry.coordinates as [number, number])
        : [2.3522, 48.8566], // Paris default
      zoom: features.length ? 12 : 10,
    });
    mapRef.current = map;

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }));
    map.addControl(new mapboxgl.FullscreenControl());
    map.addControl(new mapboxgl.ScaleControl({ maxWidth: 120, unit: "metric" }));
    map.addControl(
      new mapboxgl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
        showUserHeading: true,
      })
    );

    map.on("load", () => {
      // Terrain + sky for subtle depth
      try {
        map.setFog({
          color: "#dfe7ef",
          "horizon-blend": 0.1,
          "high-color": "#ffffff",
          "space-color": "#def",
          "star-intensity": 0,
        } as any);
        map.setTerrain({ source: "mapbox-dem", exaggeration: 1.0 });
        map.addSource("mapbox-dem", {
          type: "raster-dem",
          url: "mapbox://mapbox.mapbox-terrain-dem-v1",
          tileSize: 512,
          maxzoom: 14,
        } as any);
        // 3D buildings
        const layers = map.getStyle().layers ?? [];
        const labelLayerId = layers.find(
          (l) => l.type === "symbol" && (l.layout as any)?.["text-field"]
        )?.id;
        map.addLayer(
          {
            id: "3d-buildings",
            source: "composite",
            "source-layer": "building",
            filter: ["==", "extrude", "true"],
            type: "fill-extrusion",
            minzoom: 15,
            paint: {
              "fill-extrusion-color": "#d2d6dc",
              "fill-extrusion-height": ["get", "height"],
              "fill-extrusion-base": ["get", "min_height"],
              "fill-extrusion-opacity": 0.6,
            },
          } as any,
          labelLayerId
        );
      } catch {}
      idToCoordRef.current.clear();
      features.forEach((f) => {
        const el = document.createElement("div");
        el.className = "relative w-4 h-4";
        const ping = document.createElement("span");
        ping.className = "absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/40";
        const dot = document.createElement("span");
        dot.className = "relative inline-flex w-4 h-4 rounded-full bg-emerald-600 ring-2 ring-white shadow";
        el.appendChild(ping);
        el.appendChild(dot);

        const popupHtml = `
          <div class="space-y-2 min-w-[200px]">
            <div class="font-medium leading-tight">${f.properties.nom}</div>
            ${
              f.properties.rating !== null
                ? `<div class="text-xs text-neutral-600 inline-flex items-center gap-1"><span class="text-amber-500">★</span>${Number(
                    f.properties.rating
                  ).toFixed(1)}</div>`
                : ""
            }
            <div class="pt-1 flex items-center gap-2">
            </div>
          </div>`;

        const popup = new mapboxgl.Popup({ offset: 12 }).setHTML(popupHtml);

        new mapboxgl.Marker({ element: el })
          .setLngLat(f.geometry.coordinates as [number, number])
          .setPopup(popup)
          .addTo(map);

        idToCoordRef.current.set(
          Number(f.properties.id),
          f.geometry.coordinates as [number, number]
        );
      });

      if (features.length > 1) {
        const bounds = new mapboxgl.LngLatBounds();
        features.forEach((f) => {
          bounds.extend(f.geometry.coordinates as [number, number]);
        });
        map.fitBounds(bounds, { padding: 40, maxZoom: 14 });
      }
    });

    return () => {
      map.remove();
    };
  }, [features, token]);

  useEffect(() => {
    if (!selectedId) return;
    const map = mapRef.current;
    if (!map) return;
    const coord = idToCoordRef.current.get(Number(selectedId));
    if (!coord) return;
    map.flyTo({ center: coord, zoom: 14, speed: 1.4 });
  }, [selectedId]);

  // Ensure map fills its container and resizes correctly
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const onResize = () => map.resize();
    // slight delay after mount to ensure layout is settled
    const t = setTimeout(onResize, 50);
    window.addEventListener("resize", onResize);
    return () => {
      clearTimeout(t);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <div className="w-full h-full rounded border" ref={containerRef}>
      {!token && (
        <div className="p-4 text-sm text-red-600">
          NEXT_PUBLIC_MAPBOX_TOKEN manquant. Ajoute-le dans .env.local
        </div>
      )}
    </div>
  );
}

export default RestaurantMap;


