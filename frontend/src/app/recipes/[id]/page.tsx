import { notFound } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface RecipeDetail {
  id: number
  title: string
  description?: string

  ingredients?: string[]
  instructions?: string
}

async function getRecipe(id: string): Promise<RecipeDetail | null> {

  try {
    return await apiClient.getRecipe(id)
  } catch (error) {
    console.error('Failed to fetch recipe:', error)
    return null
  }
}

export default async function RecipePage({ params }: { params: { id: string } }) {
  const recipe = await getRecipe(params.id)
  if (!recipe) {
    notFound()
  }

  return (
    <section className="container mx-auto py-10">
      <Card>
        <CardHeader>
          <CardTitle>{recipe.title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {recipe.description && (
            <p className="text-muted-foreground">{recipe.description}</p>
          )}
          {recipe.ingredients && recipe.ingredients.length > 0 && (
            <div>
              <h2 className="font-semibold mb-2">Ingredients</h2>
              <ul className="list-disc list-inside space-y-1">
                {recipe.ingredients.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {recipe.instructions && (
            <div>
              <h2 className="font-semibold mb-2">Instructions</h2>
              <p className="whitespace-pre-line">{recipe.instructions}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  )
}

