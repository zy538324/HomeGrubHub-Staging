const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8050'

export interface Recipe {
  id: number
  title: string
  description?: string
  image_url?: string
  cuisine_type?: string
  country?: string
  difficulty?: string
  servings?: number
  prep_time?: number
  cook_time?: number
  is_private?: boolean
  user?: {
    id?: number
    username?: string
  }
  created_at?: string
  avg_rating?: number
  ingredients?: string[]
  instructions?: string
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const response = await fetch(url, {
      cache: 'no-store',
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  async getRecipes(): Promise<Recipe[]> {
    try {
      const data = await this.request('/api/recipes') as any
      // Handle different response formats
      if (Array.isArray(data)) {
        return data
      } else if (data && Array.isArray(data.recipes)) {
        return data.recipes
      } else if (data && Array.isArray(data.data)) {
        return data.data
      } else {
        console.warn('Unexpected API response format for recipes:', data)
        return []
      }
    } catch (error) {
      console.error('Failed to fetch recipes:', error)
      return []
    }
  }

  async getRecipe(id: string): Promise<Recipe | null> {
    try {
      const data = await this.request(`/api/recipes/${id}`) as any
      // Handle different response formats
      if (data && typeof data === 'object' && data.id) {
        return data
      } else if (data && data.data && typeof data.data === 'object' && data.data.id) {
        return data.data
      } else if (data && data.recipe && typeof data.recipe === 'object' && data.recipe.id) {
        return data.recipe
      } else {
        console.warn('Unexpected API response format for recipe:', data)
        return null
      }
    } catch (error) {
      console.error('Failed to fetch recipe:', error)
      return null
    }
  }

  async getFavourites(): Promise<Recipe[]> {
    try {
      const data = await this.request('/api/favourites') as any
      // Handle different response formats
      if (Array.isArray(data)) {
        return data
      } else if (data && Array.isArray(data.favourites)) {
        return data.favourites
      } else if (data && Array.isArray(data.data)) {
        return data.data
      } else {
        console.warn('Unexpected API response format for favourites:', data)
        return []
      }
    } catch (error) {
      // If endpoint doesn't exist (404), return empty array
      if (error instanceof Error && error.message.includes('404')) {
        console.warn('Favourites endpoint not found (404). This endpoint may not be implemented yet.')
        return []
      }
      console.error('Failed to fetch favourites:', error)
      return []
    }
  }

  // Add more API methods as needed
  async createRecipe(recipe: Omit<Recipe, 'id'>): Promise<Recipe> {
    return this.request<Recipe>('/api/recipes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(recipe),
    })
  }

  async updateRecipe(id: string, recipe: Partial<Recipe>): Promise<Recipe> {
    return this.request<Recipe>(`/api/recipes/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(recipe),
    })
  }

  async deleteRecipe(id: string): Promise<void> {
    await this.request(`/api/recipes/${id}`, {
      method: 'DELETE',
    })
  }
}

export const apiClient = new ApiClient(API_BASE_URL)
