import { supabase } from "../lib/supabaseClient";
import MapWithSidebar from "../components/MapWithSidebar";

type Restaurant = {
  id: number;
  photo: string | null;
  nom: string;
  rating: number | null;
  latitude: number | null;
  longitude: number | null;
  menu: string | null;
  website: string | null;
  score: number | null;
};

export default async function Home() {
  const { data, error } = await supabase
    .from("restaurants")
    .select("*");

  if (error) {
    return (
      <div className="p-6">
        <p className="text-red-600">Erreur de chargement: {error.message}</p>
      </div>
    );
  }

  const restaurants = (data ?? []) as Restaurant[];

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Restaurants</h1>
        <div className="text-sm text-neutral-500">{restaurants.length} résultats</div>
      </div>
      <MapWithSidebar restaurants={restaurants} />
    </div>
  );
}
