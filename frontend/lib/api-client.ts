/**
 * API Client for Backend Communication
 *
 * Handles all API calls to the backend Lambda functions.
 * Environment variable NEXT_PUBLIC_API_URL must be set.
 */

// ============================================================================
// Type Definitions
// ============================================================================

export interface World {
  id: string;
  theme: string;
  png_url: string;
  ply_urls: string[];
  created_at: string;
}

export interface WorldsResponse {
  worlds: World[];
}

export interface GenerateRequest {
  prompt: string;
}

export interface GenerateResponse {
  message: string;
  executionArn?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get the API base URL from environment variables
 * @throws Error if NEXT_PUBLIC_API_URL is not set
 */
function getApiBaseUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    throw new Error("NEXT_PUBLIC_API_URL environment variable is not set");
  }
  return apiUrl;
}

/**
 * Handle fetch errors and convert to user-friendly messages
 */
function handleFetchError(error: unknown): never {
  if (error instanceof Error) {
    throw new Error(`API Error: ${error.message}`);
  }
  throw new Error("An unknown error occurred while fetching data");
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch list of generated 3D worlds from the backend
 *
 * @returns Promise<World[]> - Array of available worlds
 * @throws Error if API call fails or NEXT_PUBLIC_API_URL is not set
 *
 * @example
 * const worlds = await getWorlds();
 * console.log(worlds[0].theme); // "mystic-beach"
 */
export async function getWorlds(): Promise<World[]> {
  try {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/worlds`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: WorldsResponse = await response.json();
    return data.worlds;
  } catch (error) {
    handleFetchError(error);
  }
}

/**
 * Generate a new 3D world from a text prompt
 *
 * @param prompt - Text prompt describing the desired 3D world
 * @returns Promise<GenerateResponse> - Response with execution details
 * @throws Error if API call fails or NEXT_PUBLIC_API_URL is not set
 *
 * @example
 * const response = await generateWorld("森と山が広がる幻想的な風景");
 * console.log(response.message); // "3D world generation started"
 */
export async function generateWorld(prompt: string): Promise<GenerateResponse> {
  try {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: GenerateResponse = await response.json();
    return data;
  } catch (error) {
    handleFetchError(error);
  }
}
