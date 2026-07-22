import { GoogleGenAI } from "@google/genai";
import { pipeline } from "@huggingface/transformers";
import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";


export const runtime = "nodejs";
export const dynamic = "force-dynamic";


const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

const GEMINI_MODEL = "gemini-3.6-flash";

const EMBEDDING_MODEL =
  "Xenova/all-MiniLM-L6-v2";

const INGESTION_EMBEDDING_MODEL =
  "sentence-transformers/all-MiniLM-L6-v2";

const DOCUMENT_SOURCE =
  "Human-Nutrition-2020-Edition-1598491699.pdf";

const MATCH_COUNT = 8;


if (!SUPABASE_URL) {
  throw new Error(
    "SUPABASE_URL is missing from .env.local.",
  );
}

if (!SUPABASE_SERVICE_ROLE_KEY) {
  throw new Error(
    "SUPABASE_SERVICE_ROLE_KEY is missing from .env.local.",
  );
}

if (!GEMINI_API_KEY) {
  throw new Error(
    "GEMINI_API_KEY is missing from .env.local.",
  );
}


// The service-role key must remain server-side.
const supabase = createClient(
  SUPABASE_URL,
  SUPABASE_SERVICE_ROLE_KEY,
  {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
      detectSessionInUrl: false,
    },
  },
);


const gemini = new GoogleGenAI({
  apiKey: GEMINI_API_KEY,
});


type ChatRequestBody = {
  message?: unknown;
};


type RetrievedChunk = {
  id: number;
  doc_id: string;
  chunk_index: number;
  content: string;
  metadata: {
    page?: number;
    source?: string;
    embedding_model?: string;
  } | null;
  similarity: number;
};


type FeatureExtractorOutput = {
  data: Float32Array;
};


type FeatureExtractor = (
  input: string,
  options: {
    pooling: "mean";
    normalize: boolean;
  },
) => Promise<FeatureExtractorOutput>;


let extractorPromise:
  | Promise<FeatureExtractor>
  | null = null;


/**
 * Load the MiniLM model once and reuse it for later requests.
 */
async function getEmbeddingPipeline():
Promise<FeatureExtractor> {
  if (!extractorPromise) {
    extractorPromise = pipeline(
      "feature-extraction",
      EMBEDDING_MODEL,
    ).then(
      (model) =>
        model as unknown as FeatureExtractor,
    );
  }

  return extractorPromise;
}


/**
 * Create the same normalized 384-dimensional embedding
 * format used during Python ingestion.
 */
async function embedQuery(
  query: string,
): Promise<number[]> {
  const extractor =
    await getEmbeddingPipeline();

  const output = await extractor(
    query,
    {
      pooling: "mean",
      normalize: true,
    },
  );

  const embedding = Array.from(output.data);

  if (embedding.length !== 384) {
    throw new Error(
      "Query embedding dimension mismatch. " +
      `Expected 384 but received ${embedding.length}.`,
    );
  }

  return embedding;
}


/**
 * Retrieve the most relevant chunks from Supabase.
 */
async function retrieveChunks(
  queryEmbedding: number[],
): Promise<RetrievedChunk[]> {
  const {
    data,
    error,
  } = await supabase.rpc(
    "match_documents",
    {
      query_embedding: queryEmbedding,
      match_count: MATCH_COUNT,

      // Constrain retrieval to the ingested nutrition PDF
      // and the correct embedding model.
      filter: {
        source: DOCUMENT_SOURCE,
        embedding_model:
          INGESTION_EMBEDDING_MODEL,
      },
    },
  );

  if (error) {
    throw new Error(
      `Supabase retrieval failed: ${error.message}`,
    );
  }

  return (data ?? []) as RetrievedChunk[];
}


/**
 * Build numbered context blocks containing page references.
 */
function buildContext(
  chunks: RetrievedChunk[],
): string {
  return chunks
    .map(
      (chunk, index) => {
        const page =
          chunk.metadata?.page ?? "Unknown";

        return [
          `[${index + 1}]`,
          `(Page ${page})`,
          chunk.content,
        ].join(" ");
      },
    )
    .join("\n\n");
}


/**
 * Generate a context-grounded answer with Gemini.
 */
async function generateAnswer(
  message: string,
  context: string,
): Promise<string> {
  const prompt = `
You are a strict RAG assistant.

Answer ONLY using the supplied CONTEXT.

Rules:
- Do not use outside knowledge.
- Do not invent facts.
- If the answer is not present in the context, say:
  "I couldn't find this in the provided document. Try rephrasing or asking another nutrition-related question."
- Cite sources using [1], [2], and so on.
- Include the relevant page numbers, for example: [1, p. 25].
- Give a clear and explanatory answer.
- Do not reveal private reasoning or internal analysis.

QUESTION:
${message}

CONTEXT:
${context}

ANSWER:
`.trim();

  const completion =
    await gemini.models.generateContent({
      model: GEMINI_MODEL,
      contents: prompt,
      config: {
        temperature: 0.2,
      },
    });

  const answer = completion.text?.trim();

  if (!answer) {
    throw new Error(
      "Gemini returned an empty response.",
    );
  }

  return answer;
}


export async function POST(
  req: NextRequest,
): Promise<NextResponse> {
  try {
    let body: ChatRequestBody;

    try {
      body =
        (await req.json()) as ChatRequestBody;
    } catch {
      return NextResponse.json(
        {
          error:
            "The request body must contain valid JSON.",
        },
        {
          status: 400,
        },
      );
    }

    const message =
      typeof body.message === "string"
        ? body.message.trim()
        : "";

    if (!message) {
      return NextResponse.json(
        {
          error: "Empty query",
        },
        {
          status: 400,
        },
      );
    }

    if (message.length > 2_000) {
      return NextResponse.json(
        {
          error:
            "The question must be fewer than " +
            "2,000 characters.",
        },
        {
          status: 400,
        },
      );
    }

    // 1. Embed the query using MiniLM.
    const queryEmbedding =
      await embedQuery(message);

    // 2. Retrieve matching chunks from Supabase.
    const chunks =
      await retrieveChunks(queryEmbedding);

    // Optional: show retrieval information
    // in the Next.js server terminal.
    if (
      process.env.NODE_ENV === "development"
    ) {
      console.log(
        "Retrieved chunks:",
        chunks.map((chunk) => ({
          page:
            chunk.metadata?.page ?? null,
          similarity:
            Number(
              chunk.similarity,
            ).toFixed(3),
          preview:
            chunk.content.slice(0, 100),
        })),
      );
    }

    // 3. Build numbered context with page information.
    const context = buildContext(chunks);

    // If no relevant chunks were found, return early.
    if (!context) {
      return NextResponse.json(
        {
          answer:
            "I couldn't find this in the provided " +
            "document. Try rephrasing or asking " +
            "another nutrition-related question.",
          sources: [],
        },
        {
          status: 200,
        },
      );
    }

    // 4. Ask Gemini using strict RAG instructions.
    const answer = await generateAnswer(
      message,
      context,
    );

    const sources = chunks.map(
      (chunk, index) => ({
        number: index + 1,
        page:
          chunk.metadata?.page ?? null,
        source:
          chunk.metadata?.source ??
          DOCUMENT_SOURCE,
        similarity:
          chunk.similarity,
        content:
          chunk.content.length > 300
            ? `${chunk.content.slice(0, 300)}...`
            : chunk.content,
      }),
    );

    return NextResponse.json(
      {
        answer,
        sources,
      },
      {
        status: 200,
      },
    );
  } catch (error) {
    console.error(
      "RAG chat API error:",
      error,
    );

    const details =
      error instanceof Error
        ? error.message
        : "Unknown server error";

    return NextResponse.json(
      {
        error:
          "Unable to generate an answer.",
        details:
          process.env.NODE_ENV ===
          "development"
            ? details
            : undefined,
      },
      {
        status: 500,
      },
    );
  }
}