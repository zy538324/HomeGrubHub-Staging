import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <section className="py-16 text-center space-y-8">
      <h1 className="text-4xl font-bold">Welcome to HomeGrubHub</h1>
      <p className="text-lg text-muted-foreground">
        Discover, save, and share your favorite recipes from around the world
      </p>
      <form className="flex justify-center">
        <input
          type="text"
          placeholder="Search recipes, ingredients, or cuisines..."
          className="w-1/2 border rounded-l px-4 py-2"
        />
        <Button type="submit" className="rounded-l-none">Search</Button>
      </form>
    </section>
  )
}
