import Link from "next/link"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { apiClient, type Recipe } from "@/lib/api"

async function getRecipes(): Promise<Recipe[]> {
  try {
    return await apiClient.getRecipes()
  } catch (error) {
    console.error('Failed to fetch recipes:', error)
    return []
  }
}

export const metadata = {
  title: "All Recipes",
}

export default async function RecipesPage() {
  const recipes = await getRecipes()

  // Ensure recipes is an array
  const recipesArray = Array.isArray(recipes) ? recipes : []

  if (recipesArray.length === 0) {
    return (
      <section className="container mx-auto py-10">
        <div className="flex flex-col items-center text-center gap-4">
          <h2 className="text-2xl font-semibold">No Recipes Found</h2>
          <p className="text-muted-foreground">
            Be the first to add a recipe!
          </p>
          <Button asChild>
            <Link href="/add-recipe">Add Recipe</Link>
          </Button>
        </div>
      </section>
    )
  }

  return (
    <section className="container mx-auto py-10">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold mb-2">All Recipes</h1>
        <p className="text-muted-foreground">
          Browse our collection of delicious recipes from around the world
        </p>
      </div>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {recipesArray.map((recipe) => (
          <Card key={recipe.id} className="flex flex-col">
            <CardHeader>
              <CardTitle>{recipe.title}</CardTitle>
            </CardHeader>
            <CardContent className="flex-1">
              <p className="text-sm text-muted-foreground">
                {recipe.description ?? "A tasty recipe to try."}
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

