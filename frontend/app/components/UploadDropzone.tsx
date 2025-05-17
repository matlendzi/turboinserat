import { useCallback, useState } from "react";

export default function UploadDropzone({
  onFileSelected,
}: {
  onFileSelected: (file: File) => void;
}) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelected(file);
  }, [onFileSelected]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  };

  return (
    <label
    htmlFor="file-upload"
    onDrop={handleDrop}
    onDragOver={(e) => {
      e.preventDefault();
      setIsDragging(true);
    }}
    onDragLeave={() => setIsDragging(false)}
    className={`flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-xl cursor-pointer transition ${
      isDragging
        ? "border-blue-500 bg-blue-50"
        : "border-gray-300 bg-white dark:bg-gray-900"
    }`}
  >
      <input
        id="file-upload"
        type="file"
        accept="image/*"
        onChange={handleChange}
        className="hidden"
      />
      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        <strong>Datei hierher ziehen</strong> oder klicken zum Hochladen
      </p>
    </label>
  );
}
