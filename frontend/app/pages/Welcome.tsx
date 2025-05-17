export default function Welcome() {
  return (
    <main className="flex items-center justify-center pt-16 pb-4">
      <div className="text-center space-y-4">
        <h1 className="text-2xl font-bold">Willkommen zur KI-Kleinanzeigen-App</h1>
        <p className="text-gray-600 dark:text-gray-300">Hier beginnt deine Reise.</p>
        <a
          href="/wizard"
          className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Starte den Wizard
        </a>
      </div>
    </main>
  );
}
