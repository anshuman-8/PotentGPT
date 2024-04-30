import { useState } from "react";
import Card from "./Card";
import Details from "./Details";

const Component = () => {
  const [prompt, setPrompt] = useState(
    "Looking for a catering service for a wedding party with approximately 50 guests."
  );
  const [location, setLocation] = useState("Santa Clara, CA");
  const [isLocationBased, setIsLocationBased] = useState(false);
  const [country, setCountry] = useState("US");
  const [response, setResponse] = useState({});
  const [loading, setLoading] = useState(false);
  const [vendors, setVendors] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleSearch = async () => {
    setErrorMsg(null);
    if (!prompt || !country) {
      setErrorMsg("All fields are required");
      return;
    }
    let loc = "-";
    if (isLocationBased) {
      loc = location.replace(" ", "%20");
    }
    const cou = country.replace(" ", "%20");
    const pro = prompt.replace(" ", "%20");

    setLoading(true);
    try {
      const end_point = `/static/?prompt=${pro}&location=${loc}&country_code=${cou}`;
      const url = `${process.env.REACT_APP_BACKEND_URL}${end_point}`;
      console.log("Searching :", url);
      const response = await fetch(url, {
        method: "GET",
      });

      if (response.status === 500) {
        console.log("Error");
        setLoading(false);
        setResponse({});
        setVendors([]);
        try {
          const data = await response.json();
          setErrorMsg(
            `Error : ${data.detail.message};  \t\n Id : ${data.detail.id}`
          );
          return;
        } catch (err) {
          setErrorMsg(`Error : ${response.statusText}`);
          return;
        }
      }
      const data = await response.json();
      console.log("The response: ", data);
      setResponse(data);
      setVendors(data.results);
    } catch (err) {
      console.log(err);
      setLoading(false);
    }
    setLoading(false);
  };

  return (
    <div className="container mx-auto p-4">
      {/* Input boxes */}
      <h1 className="text-2xl font-semibold">
        SearchProbe{" "}
        <span className="font-thin text-pretty border rounded-xl p-1 text-sm">
          Experimental
        </span>
      </h1>
      <div className="mb-4 py-8">
        <div className="flex w-full">
          <div className="flex flex-col mr-4 w-2/3">
            <label htmlFor="prompt" className="text-sm mb-1">
              Goal:
            </label>
            <textarea
              id="prompt"
              className="border p-2"
              placeholder="Prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>

          <div className="flex flex-col w-1/6 ">
            <label htmlFor="country" className="text-sm mb-1">
              Country Code:
            </label>
            <input
              id="country"
              className="border px-2 py-4"
              type="text"
              placeholder="Country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
            />
          </div>
        </div>
        <div className="my-5">
          <div className="flex items-center space-x-2">
            <span className="font-semibold">Is it a location based goal?</span>
            <input
              type="checkbox"
              checked={isLocationBased}
              onChange={() => setIsLocationBased(!isLocationBased)}
              className="h-5 w-5 text-blue-500 focus:ring-1 focus:ring-blue-500 focus:ring-offset-2"
            />
          </div>
          {isLocationBased && (
            <div className="flex flex-col mr-4 w-1/6">
              <label htmlFor="location" className="text-sm mb-1">
                Location:
              </label>
              <input
                id="location"
                className="border px-2 py-4"
                type="text"
                placeholder="Location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
          )}
        </div>

        <div>
          <button
            className={`border py-3 px-6 mt-2 text-lg ${
              loading
                ? "cursor-not-allowed opacity-50"
                : "hover:bg-slate-500 hover:text-white"
            }`}
            onClick={handleSearch}
            disabled={loading}
          >
            {loading ? (
              <div className="flex items-center">
                <div className="animate-spin h-4 w-4 border-t-2 border-slate-800 border-solid rounded-full mr-2"></div>
                Searching...
              </div>
            ) : (
              "Search"
            )}
          </button>
        </div>
      </div>
      {Object.keys(response).length > 0 && <Details data={response} />}
      {/* Grid of cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-4">
        {vendors.length > 0 ? (
          vendors.map((item, index) => <Card key={index} vendor={item} location={response.location} />)
        ) : (
          <div>No results</div>
        )}
        {errorMsg && (
          <div className="col-span-4 text-red-500 text-center">{errorMsg}</div>
        )}
      </div>
    </div>
  );
};

export default Component;
