import React from "react";

export default function Card({ vendor }) {
  const { name, contacts, source, provider } = vendor;

  return (
    <div className="border p-4 rounded-md shadow-md hover:shadow-xl">
      <h2 className="text-xl font-semibold">{name}</h2>
      {vendor.info && <p className="text-gray-600">{vendor.info}</p>}

      <div className="mt-4">
        <strong>Contact Information:</strong>
        <p>
          Email:{" "}
          {contacts.email instanceof Array
            ? contacts.email.join(", ")
            : contacts.email}
        </p>
        <p>
          Phone:{" "}
          {contacts.phone instanceof Array
            ? contacts.phone.join(", ")
            : contacts.phone}
        </p>
        <p>Address: {contacts.address}</p>
      </div>

      <div className="mt-4">
        <strong>Additional Information:</strong>
        <p>
          Source:{" "}
          <a
            href={source}
            target="_blank"
            rel="noopener noreferrer"
            className="overflow-auto truncate block max-w-full text-blue-500"
          >
            {source}
          </a>
        </p>
        <p>Provider: {provider.join(", ")}</p>
      </div>
    </div>
  );
}
