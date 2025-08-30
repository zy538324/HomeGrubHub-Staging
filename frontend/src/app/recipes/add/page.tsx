import { Metadata } from "next"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

export const metadata: Metadata = {
  title: "Add Recipe",
  description: "Create a new recipe",
}

export default function AddRecipePage() {
  return (
    <div className="container mx-auto max-w-3xl py-10">
      <Card>
        <CardHeader className="bg-primary text-primary-foreground rounded-t-lg">
          <CardTitle className="text-white">Add Recipe</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="title" className="font-semibold">
              Title
            </Label>
            <Input id="title" placeholder="Grandma's Apple Pie" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description" className="font-semibold">
              Description
            </Label>
            <Textarea id="description" placeholder="A short summary of the recipe" />
          </div>

          <div className="grid gap-6 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="prepTime" className="font-semibold">
                Prep Time (min)
              </Label>
              <Input id="prepTime" type="number" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cookTime" className="font-semibold">
                Cook Time (min)
              </Label>
              <Input id="cookTime" type="number" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="servings" className="font-semibold">
                Servings
              </Label>
              <Input id="servings" type="number" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="difficulty" className="font-semibold">
                Difficulty
              </Label>
              <select
                id="difficulty"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="country" className="font-semibold">
                Country of Origin
              </Label>
              <Input id="country" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cuisineType" className="font-semibold">
                Cuisine Type
              </Label>
              <Input id="cuisineType" />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="ingredients" className="font-semibold">
              Ingredients
            </Label>
            <Textarea id="ingredients" placeholder="List each ingredient on a new line" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="method" className="font-semibold">
              Method
            </Label>
            <Textarea id="method" placeholder="Step-by-step cooking instructions" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="tags" className="font-semibold">
              Tags
            </Label>
            <Input id="tags" placeholder="e.g. vegetarian, quick" />
          </div>

          <div className="grid gap-6 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="calories" className="font-semibold">
                Calories
              </Label>
              <Input id="calories" type="number" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="protein" className="font-semibold">
                Protein (g)
              </Label>
              <Input id="protein" type="number" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="fat" className="font-semibold">
                Fat (g)
              </Label>
              <Input id="fat" type="number" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="carbs" className="font-semibold">
                Carbs (g)
              </Label>
              <Input id="carbs" type="number" />
            </div>
          </div>
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit">Save Recipe</Button>
        </CardFooter>
      </Card>
    </div>
  )
}

