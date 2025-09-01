import Link from "next/link"
import { HeartIcon } from "@radix-ui/react-icons"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface Recipe {
  id: number
  title: string
  description?: string
  difficulty?: string
  total_time?: number
  country?: string
}

async function getFavourites(): Promise<Recipe[]> {
  const res = await fetch("/api/favourites", { cache: "no-store" })
  if (!res.ok) {
    return []
  }
  return res.json()
}

export default async function FavouritesPage() {
  const recipes = await getFavourites()

  if (recipes.length === 0) {
    return (
      <section className="container mx-auto py-10">
        <div className="flex flex-col items-center text-center gap-4">
          <HeartIcon className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-2xl font-semibold">No Favourite Recipes Yet</h2>
          <p className="text-muted-foreground">
            Start building your favourites collection by hearting recipes you love!
          </p>
          <Button asChild>
            <Link href="/">Browse Recipes</Link>
          </Button>
        </div>
      </section>
    )
  }

  return (
    <section className="container mx-auto py-10">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold mb-2 flex items-center justify-center gap-2">
          <HeartIcon className="h-8 w-8 text-primary" /> My Favourite Recipes
        </h1>
        <p className="text-muted-foreground">
          Your personally curated collection of favourite recipes
        </p>
      </div>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {recipes.map((recipe) => (
          <Card key={recipe.id} className="flex flex-col">
            <CardHeader>
              <CardTitle>{recipe.title}</CardTitle>
            </CardHeader>
            <CardContent className="flex-1">
              <p className="text-sm text-muted-foreground">
                {recipe.description ??
                  "A delicious recipe in your favourites collection."}
              </p>
            </CardContent>
            <CardFooter className="flex justify-between items-center">
              <div className="flex gap-2 text-xs text-muted-foreground">
                {recipe.difficulty && (
                  <span className="rounded bg-secondary px-2 py-1">
                    {recipe.difficulty}
                  </span>
                )}
                {recipe.total_time && (
                  <span className="rounded bg-secondary px-2 py-1">
                    {recipe.total_time} min
                  </span>
                )}
                {recipe.country && (
                  <span className="rounded bg-secondary px-2 py-1">
                    {recipe.country}
                  </span>
                )}
              </div>
              <Button asChild size="sm">
                <Link href={`/recipes/${recipe.id}`}>View Recipe</Link>
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </section>
  )
}
