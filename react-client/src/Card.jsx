import React from "react";

export default function Card({ vendor, location }) {
  const { name, contacts, source, provider, target } = vendor;

  const [yelpSearch, setYelpSearch] = React.useState(false);
  const [yelpData, setYelpData] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [errorMsg, setErrorMsg] = React.useState(null);

  const searchYelp = async () => {
    if (!location) {
      return;
    }
    const request_body = JSON.stringify({
      vendor: vendor,
      location: location,
      country_code: "US"
    })
    console.log("Searching Yelp :",request_body);
    try {
      const end_point = "/static/reverse-yelp/";
      const url = `${process.env.REACT_APP_BACKEND_URL}${end_point}`;
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: request_body,
      });

      const data = await response.json();
      setYelpSearch(true);
      if (data.detail) {
        setErrorMsg(data.detail);
        return;
      }
      console.log("The response: ", data);
      setYelpData(data);
    } catch (err) {
      console.log(err);
      setLoading(false);
    }
  }

  return (
    <div className="border p-4 rounded-md shadow-md hover:shadow-xl">
      <h2 className="text-xl font-semibold">{name}</h2>
      <div className="text-base text-slate-400 px-1">{target}</div>
      {vendor.info && <p className="text-gray-600">{vendor.info}</p>}

      {
        vendor.latitude && vendor.longitude && (
          <a className="mt-4 border rounded-md p-1 mx-1 my-2 bg-gray-200 hover:shadow-md" href={`https://maps.google.com/?q=${vendor.latitude},${vendor.longitude}`}>
            {"Location ->"}
          </a>
        )
      }
      {
        vendor.rating && (
          <div className="mt-4">
            <strong>Rating:</strong>
            <span className="px-2">{vendor.rating} <span className="text-slate-500">({vendor.rating_count})</span></span>
          </div>
        )
      }
      <div>

      {( !vendor.rating && !yelpSearch) && (
        <button onClick={searchYelp} className="mt-2 border rounded-md p-1 mx-1 my-2 bg-gray-200 hover:shadow-md">Search Yelp{loading&& <span className="animate-spin"/>}</button>
      )}
      {errorMsg && <div className="text-orange-300">{errorMsg}</div>}
      {(yelpData && !errorMsg) && (
        <div>
          <strong>Yelp Rating:</strong>
          <span className="px-2">{yelpData.rating} <span className="text-slate-500">({yelpData.rating_count})</span></span>
          <br/>
          {
            yelpData.latitude && yelpData.longitude && (
              <a className="mt-4 border rounded-md p-1 mx-1 my-2 bg-gray-200 hover:shadow-md" href={`https://maps.google.com/?q=${yelpData.latitude},${yelpData.longitude}`}>
                {"Location ->"}
              </a>
            )
          }
        </div>
      )}
      </div>


      <div className="mt-3">
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
