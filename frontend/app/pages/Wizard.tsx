import { useState } from "react";
import UploadDropzone from "../components/UploadDropzone";
import StepIndicator from "../components/StepIndicator";
import { ClipboardDocumentIcon } from "@heroicons/react/24/outline";
import API from "../../services/api";
import BlockingOverlay from "../components/BlockingOverlay";

const formatPrice = (price: string | number): string => {
  if (!price) return "";
  const numPrice = typeof price === "string" ? parseFloat(price) : price;
  return numPrice.toLocaleString("de-DE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + " €";
};

const steps = [
  { label: "Upload" },
  { label: "Merkmale prüfen" },
  { label: "Preis&shy;vorschlag" },
  { label: "Abschluss" },
];

export default function Wizard() {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [adProcessId, setAdProcessId] = useState<string | null>(null);
  const [attributes, setAttributes] = useState({
    title: "",
    description: "",
    brand: "",
    model_or_type: "",
    category: "",
    color: "",
    condition: "",
    special_notes: "",
  });
  const [suggestion, setSuggestion] = useState({
    suggested_price: "",
    explanation: "",
  });
  const [price, setPrice] = useState("");
  const [loading, setLoading] = useState(false);
  const [priceLoading, setPriceLoading] = useState(false);
  const [listingLoading, setListingLoading] = useState(false);
  const [blockingMessage, setBlockingMessage] = useState<string | null>(null);

  const showBlockingMessage = async (
    message: string,
    action: () => Promise<void>
  ) => {
    setBlockingMessage(message);
    const start = Date.now();
    try {
      await action();
    } catch (err) {
      console.error(err);
    } finally {
      const elapsed = Date.now() - start;
      const remaining = 5000 - elapsed;
      if (remaining > 0) {
        setTimeout(() => setBlockingMessage(null), remaining);
      } else {
        setBlockingMessage(null);
      }
    }
  };

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const uploadImageAndGetUrl = async (): Promise<string> => {
    if (!selectedFile) throw new Error("Keine Datei ausgewählt");
    const formData = new FormData();
    formData.append("file", selectedFile);
    const response = await API.post<{ url: string }>("/api/upload/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data.url;
  };

  const startAnalysis = async () => {
    await showBlockingMessage(
      "Die KI analysiert dein Bild und erkennt Marke, Modell sowie Kategorie...",
      async () => {
        setLoading(true);
        try {
          const imageUrl = await uploadImageAndGetUrl();
          const payload: { image_urls: string[]; ad_process_id?: string } = {
            image_urls: [imageUrl],
          };
          if (adProcessId) payload.ad_process_id = adProcessId;

          const { data } = await API.post<{
            ad_process_id: string;
            identification: Record<string, any>;
          }>("/api/identify", payload);

          setAdProcessId(data.ad_process_id);
          setAttributes((prev) => ({ ...prev, ...data.identification }));
          setCurrentStep(1);
        } catch (err: any) {
          console.error("Identify-Error:", err.response?.data || err.message);
        } finally {
          setLoading(false);
        }
      }
    );
  };

  const fetchPriceSuggestion = async () => {
    if (!adProcessId) return;
    await API.post("/api/price/comparables", { ad_process_id: adProcessId });
    const response = await API.post<{
      suggested_price: string;
      explanation: string;
    }>("/api/price/suggest", { ad_process_id: adProcessId });
    setSuggestion(response.data);
    setPrice(formatPrice(response.data.suggested_price));
  };

  const fetchListing = async () => {
    if (!adProcessId) return;
    try {
      await API.post("/api/listing/generate", { ad_process_id: adProcessId });
      const { data } = await API.get(`/api/listing/ad-process/${adProcessId}`);
      const listing = data.listing;
      if (listing) {
        setAttributes((prev) => ({
          ...prev,
          title: listing.title,
          description: listing.description,
          condition: listing.condition,
          category: listing.category,
        }));
        setPrice(formatPrice(listing.price));
      }
    } catch (err: any) {
      console.error("Listing-Fetch fehlgeschlagen:", err.response?.data || err.message);
    }
  };

  const goNext = async () => {
    if (currentStep === 0) {
      await startAnalysis();
    } else if (currentStep === 1) {
      await showBlockingMessage(
        "Die KI analysiert Vergleichsangebote für dein Produkt...",
        async () => {
          setPriceLoading(true);
          await fetchPriceSuggestion();
          setCurrentStep(2);
          setPriceLoading(false);
        }
      );
    } else if (currentStep === 2) {
      await showBlockingMessage(
        "Die KI generiert deine Verkaufsanzeige...",
        async () => {
          setListingLoading(true);
          await fetchListing();
          setCurrentStep(3);
          setListingLoading(false);
        }
      );
    } else {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const copyToClipboard = (text: string) => navigator.clipboard.writeText(text);

  return (
    <div className="relative max-w-xl mx-auto p-6 space-y-6">
      {/* Blocking overlay */}
      {blockingMessage && <BlockingOverlay message={blockingMessage} />}

      <h1 className="text-2xl font-bold text-center">Kleinanzeigen KI-Wizard</h1>
      <StepIndicator steps={steps} currentStep={currentStep} />

      {/* Step 0: Upload */}
      {currentStep === 0 && (
        <>
          {!loading && <UploadDropzone onFileSelected={handleFileSelect} />}
          {previewUrl && (
            <div className="mt-4 flex justify-center">
              <img src={previewUrl} alt="Vorschau" className="max-h-48 rounded shadow" />
            </div>
          )}
          <div className="flex justify-center">
            <button
              onClick={goNext}
              disabled={!selectedFile}
              className="mt-6 px-6 py-2 rounded-xl text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? "Analysiere..." : "KI-Analyse starten"}
            </button>
          </div>
        </>
      )}

      {/* Step 1: Attributes */}
      {currentStep === 1 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Marke</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={attributes.brand}
              onChange={e => setAttributes({ ...attributes, brand: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Modell oder Typ</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={attributes.model_or_type}
              onChange={e => setAttributes({ ...attributes, model_or_type: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Kategorie</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={attributes.category}
              onChange={e => setAttributes({ ...attributes, category: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Farbe</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={attributes.color}
              onChange={e => setAttributes({ ...attributes, color: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Zustand</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={attributes.condition}
              onChange={e => setAttributes({ ...attributes, condition: e.target.value })}
            >
              <option>Neu</option>
              <option>Sehr Gut</option>
              <option>Gut</option>
              <option>In Ordnung</option>
              <option>Defekt</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Hinweise</label>
            <textarea
              className="w-full border rounded px-3 py-2 h-24"
              value={attributes.special_notes}
              onChange={e => setAttributes({ ...attributes, special_notes: e.target.value })}
            />
          </div>
          <div className="flex justify-center">
            <button
              onClick={goNext}
              className="mt-4 px-6 py-2 rounded-xl text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              disabled={priceLoading}
            >
              {priceLoading ? "Preisvorschlag wird ermittelt..." : "Preisvorschlag ermitteln"}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Price suggestion */}
      {currentStep === 2 && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-center">Preisvorschlag</h2>
          <div className="space-y-2">
            <div><strong>Preisvorschlag:</strong> {formatPrice(suggestion.suggested_price)}</div>
            <div><strong>Erklärung:</strong> {suggestion.explanation}</div>
          </div>
          <div className="flex justify-center">
            <button
              onClick={goNext}
              className="mt-4 px-6 py-2 rounded-xl text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              disabled={listingLoading}
            >
              {listingLoading ? "Verkaufsanzeige wird generiert..." : "Verkaufsanzeige generieren"}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Final */}
      {currentStep === 3 && (
        <div className="space-y-8 max-w-2xl mx-auto">
          <h2 className="text-2xl font-bold text-center text-gray-100">Abschluss</h2>
          {loading && <p className="text-center text-gray-400">Lade Listing...</p>}
          {!loading && (
            <>
              {previewUrl && (
                <div className="mt-4 flex justify-center">
                  <img src={previewUrl} alt="Vorschau" className="max-h-24 rounded shadow" />
                </div>
              )}
              <div className="space-y-6 bg-gray-800 rounded-xl p-6 shadow-sm divide-y divide-gray-700">
                {[
                  ["Titel", attributes.title],
                  ["Beschreibung", attributes.description],
                  ["Kategorie", attributes.category],
                  ["Zustand", attributes.condition],
                  ["Preis", formatPrice(price)],
                ].map(([label, value]) => (
                  <div key={label as string} className="group relative py-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-300 mb-1">{label}</label>
                        <p className={`text-gray-400 ${label === "Beschreibung" ? "whitespace-pre-wrap" : ""}`}>
                          {value as string}
                        </p>
                      </div>
                      <button
                        onClick={() => copyToClipboard(value as string)}
                        className="ml-4 p-2 text-gray-500 hover:text-gray-200 rounded-full hover:bg-gray-700"
                        title="In Zwischenablage kopieren"
                      >
                        <ClipboardDocumentIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-center">
                <button
                  onClick={() => {
                    setCurrentStep(0);
                    setSelectedFile(null);
                    setPreviewUrl(null);
                    setAdProcessId(null);
                    setAttributes({
                      title: "",
                      description: "",
                      brand: "",
                      model_or_type: "",
                      category: "",
                      color: "",
                      condition: "",
                      special_notes: "",
                    });
                    setSuggestion({
                      suggested_price: "",
                      explanation: "",
                    });
                    setPrice("");
                  }}
                  className="px-8 py-3 rounded-xl text-white bg-green-500 hover:bg-green-600 transition-colors duration-200"
                >
                  Neustart
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
