import React from "react";

export default function Details({
  prompt,
  id,
  time,
  count,
  query,
  solution,
  searchSpace,
}) {
  return (
    <div className="my-5">
      {/* {searchSpace}
      {solution} */}
      <h2 className="font-semibold text-lg">Details</h2>
      <div className="flex flex-col justify-start space-y-4">
        <div className="flex flex-row space-x-6 justify-start">
          <h3>
            <span className="font-bold">Id:</span> {id}
          </h3>
          <h3>
            <span className="font-bold">Time (seconds):</span> {time}
          </h3>
          <h3>
            <span className="font-bold">No. of Results:</span> {count}
          </h3>
        </div>
        <div className="flex flex-row space-x-6 justify-start">
          <h3>
            <span className="font-bold">Search Query:</span> {query}
          </h3>
          <h3>
            <span className="font-bold">Solution:</span> {solution}
          </h3>
          <h3>
            <span className="font-bold">Search Space:</span> {searchSpace.join(", ")}
          </h3>
        </div>
      </div>
    </div>
  );
}
