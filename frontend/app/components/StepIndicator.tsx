interface Step {
    label: string;
  }
  
  export default function StepIndicator({
    steps,
    currentStep,
  }: {
    steps: Step[];
    currentStep: number;
  }) {
    return (
      <div className="mb-6 flex justify-between">
        {steps.map((step, index) => {
          const isActive = index === currentStep;
          const isDone = index < currentStep;
  
          return (
            <div key={index} className="flex flex-col items-center flex-1">
              <div
                className={`w-6 h-6 sm:w-8 sm:h-8 flex items-center justify-center rounded-full text-xs sm:text-sm font-semibold ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : isDone
                    ? "bg-blue-300 text-white"
                    : "bg-gray-300 text-gray-700"
                }`}
              >
                {index + 1}
              </div>
              <span className="mt-1 text-xs sm:text-sm text-center whitespace-normal break-words leading-tight max-w-[60px] sm:max-w-none" dangerouslySetInnerHTML={{ __html: step.label }} />
            </div>
          );
        })}
      </div>
    );
  }
  