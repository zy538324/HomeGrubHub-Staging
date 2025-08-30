import Link from "next/link"
import { NavigationMenu, NavigationMenuItem, NavigationMenuLink, NavigationMenuList } from "@radix-ui/react-navigation-menu"

export function Navbar() {
  return (
    <nav className="bg-primary text-primary-foreground">
      <NavigationMenu className="container mx-auto">
        <NavigationMenuList className="flex gap-4 p-4">
          <NavigationMenuItem>
            <NavigationMenuLink asChild>
              <Link href="/" className="font-semibold hover:text-secondary">
                Home
              </Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
          <NavigationMenuItem>
            <NavigationMenuLink asChild>
              <Link href="/about" className="font-semibold hover:text-secondary">
                About
              </Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink asChild>
                <Link href="/recipes" className="font-semibold hover:text-secondary">
                  Recipes
                </Link>
              </NavigationMenuLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink asChild>
                <Link href="/recipes/add" className="font-semibold hover:text-secondary">
                  Add Recipe
                </Link>
              </NavigationMenuLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink asChild>
                <Link href="/favourites" className="font-semibold hover:text-secondary">
                  Favourites
                </Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
          <NavigationMenuItem>
            <NavigationMenuLink asChild>
              <Link href="/legal/privacy-policy" className="font-semibold hover:text-secondary">
                Privacy
              </Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
          <NavigationMenuItem>
            <NavigationMenuLink asChild>
              <Link href="/legal/terms-of-service" className="font-semibold hover:text-secondary">
                Terms
              </Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
          <NavigationMenuItem>
            <NavigationMenuLink asChild>
              <Link href="/login" className="font-semibold hover:text-secondary">
                Login
              </Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
          <NavigationMenuItem>
            <NavigationMenuLink asChild>
              <Link href="/register" className="font-semibold hover:text-secondary">
                Register
              </Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
        </NavigationMenuList>
      </NavigationMenu>
    </nav>
  )
}
