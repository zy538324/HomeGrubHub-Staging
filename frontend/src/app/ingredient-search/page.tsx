"use client"

import { useRef, useState } from "react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  MagnifyingGlassIcon,
  QuestionMarkCircledIcon,
  ListBulletIcon,
  Crosshair1Icon,
} from "@radix-ui/react-icons"

const suggestionGroups = [
  {
    title: "Protein Base",
    color: "bg-primary",
    tags: ["chicken", "beef", "fish", "eggs", "tofu"],
  },
  {
    title: "Vegetables",
    color: "bg-secondary",
    tags: ["onions", "garlic", "tomatoes", "peppers", "mushrooms"],
  },
  {
    title: "Staples",
    color: "bg-yellow-500",
    tags: ["rice", "pasta", "potatoes", "bread", "flour"],
  },
]

export default function IngredientSearchPage() {
  const [ingredients, setIngredients] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleTagClick = (tag: string) => {
    const list = ingredients
      .split(",")
      .map((i) => i.trim().toLowerCase())
      .filter(Boolean)
    if (!list.includes(tag.toLowerCase())) {
      const next = ingredients ? `${ingredients}, ${tag}` : tag
      setIngredients(next)
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = "auto"
      el.style.height = `${el.scrollHeight}px`
    }
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    // Basic submission placeholder
    await fetch("/api/search-by-ingredients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ingredients }),
    })
  }

  return (
    <div className="container space-y-16 py-8">
      <header className="text-center space-y-4">
        <h1 className="text-4xl font-bold flex items-center justify-center gap-2">
          <MagnifyingGlassIcon className="h-8 w-8 text-secondary" />
          Find Recipes by Ingredients
        </h1>
        <p className="text-lg text-muted-foreground">
          Enter the ingredients you have and discover recipes you can make!
        </p>
        <hr className="w-24 mx-auto border-t-2 border-secondary" />
      </header>

      <Card className="max-w-2xl mx-auto">
        <CardContent className="p-6 space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <label htmlFor="ingredients" className="text-lg font-semibold flex items-center gap-2">
              <ListBulletIcon className="h-5 w-5 text-secondary" />
              What ingredients do you have?
            </label>
            <Textarea
              id="ingredients"
              ref={textareaRef}
              value={ingredients}
              onChange={(e) => setIngredients(e.target.value)}
              onInput={handleInput}
              rows={4}
              placeholder="Enter ingredients separated by commas, e.g., chicken, tomatoes, onions..."
              required
            />
            <p className="text-sm text-muted-foreground">
              Tip: Separate ingredients with commas. Be specific (e.g., “chicken breast” instead of just “chicken”).
            </p>
            <Button type="submit" className="w-full">
              <MagnifyingGlassIcon className="mr-2 h-5 w-5" />
              Find Matching Recipes
            </Button>
          </form>
        </CardContent>
      </Card>

      <section className="space-y-8">
        <h2 className="text-2xl font-semibold text-center flex items-center justify-center gap-2">
          <QuestionMarkCircledIcon className="h-6 w-6 text-secondary" />
          How it works
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="text-center space-y-3">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground">
              <ListBulletIcon className="h-8 w-8" />
            </div>
            <h5 className="font-semibold">1. List Your Ingredients</h5>
            <p className="text-muted-foreground">
              Enter the ingredients you have available in your kitchen, separated by commas.
            </p>
          </div>
          <div className="text-center space-y-3">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
              <MagnifyingGlassIcon className="h-8 w-8" />
            </div>
            <h5 className="font-semibold">2. We Search &amp; Match</h5>
            <p className="text-muted-foreground">
              Our system searches through all recipes and finds the best matches based on your ingredients.
            </p>
          </div>
          <div className="text-center space-y-3">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-yellow-500 text-white">
              <Crosshair1Icon className="h-8 w-8" />
            </div>
            <h5 className="font-semibold">3. Cook &amp; Enjoy</h5>
            <p className="text-muted-foreground">
              Choose from the matched recipes and start cooking with what you already have!
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <h3 className="text-xl font-semibold flex items-center gap-2">
          <QuestionMarkCircledIcon className="h-5 w-5 text-secondary" />
          Popular Ingredient Combinations
        </h3>
        <div className="grid gap-4 md:grid-cols-3">
          {suggestionGroups.map((group) => (
            <Card key={group.title} className="bg-muted" >
              <CardContent className="p-4 space-y-2">
                <h6 className={`font-semibold text-sm ${group.color.replace("bg-", "text-")}`}>{group.title}</h6>
                <div className="flex flex-wrap gap-1">
                  {group.tags.map((tag) => (
                    <span
                      key={tag}
                      onClick={() => handleTagClick(tag)}
                      className={`${group.color} text-white px-2 py-1 rounded cursor-pointer text-sm transition-transform hover:scale-105`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  )
}

