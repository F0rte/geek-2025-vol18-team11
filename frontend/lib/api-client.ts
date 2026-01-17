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

// Future: Generate endpoint types (commented out for now)
// export interface GenerateRequest {
//     prompt_ja: string;
//     seed?: number;
//     classes?: string;
// }
//
// export interface GenerateResponse {
//     execution_arn: string;
//     execution_id: string;
//     theme: string;
//     prompt_en: string;
//     status: string;
// }

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

// Future: Generate endpoint (commented out for now)
// export async function generateWorld(request: GenerateRequest): Promise<GenerateResponse> {
//     try {
//         const baseUrl = getApiBaseUrl();
//         const response = await fetch(`${baseUrl}/generate`, {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json",
//             },
//             body: JSON.stringify(request),
//         });
//
//         if (!response.ok) {
//             throw new Error(`HTTP ${response.status}: ${response.statusText}`);
//         }
//
//         const data: GenerateResponse = await response.json();
//         return data;
//     } catch (error) {
//         handleFetchError(error);
//     }
// }
