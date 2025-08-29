import Link from "next/link"
import { NavigationMenu, NavigationMenuItem, NavigationMenuLink, NavigationMenuList } from "@radix-ui/react-navigation-menu"

export function Navbar() {
  return (
    <nav className="border-b">
      <NavigationMenu className="container mx-auto">
        <NavigationMenuList className="flex gap-4 p-4">
          <NavigationMenuItem>
            <NavigationMenuLink asChild>
              <Link href="/" className="font-semibold">Home</Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
          <NavigationMenuItem>
            <NavigationMenuLink asChild>
              <Link href="/about" className="font-semibold">About</Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
        </NavigationMenuList>
      </NavigationMenu>
    </nav>
  )
}
