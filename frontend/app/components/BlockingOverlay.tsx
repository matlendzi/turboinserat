import React from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";

interface BlockingOverlayProps {
  message: string;
}

export default function BlockingOverlay({ message }: BlockingOverlayProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-80 flex flex-col items-center justify-center transition-opacity duration-300">
      <ArrowPathIcon className="h-12 w-12 text-white animate-spin mb-4" />
      <p className="text-white text-lg text-center max-w-xs px-4">{message}</p>
    </div>
  );
}
