#include <vector>
#include <string>
#include <stdexcept>

#ifdef HAS_ONNXRUNTIME
#include <onnxruntime_cxx_api.h>
#endif

namespace hydra {

class OnnxRunner {
public:
    OnnxRunner([[maybe_unused]] const std::string& model_path) {
#ifdef HAS_ONNXRUNTIME
        Ort::SessionOptions opts;
        opts.SetIntraOpNumThreads(4);
        opts.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        env_ = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "hydra");
        session_ = std::make_unique<Ort::Session>(*env_, model_path.c_str(), opts);
#endif
    }

    std::vector<float> predict(const std::vector<float>& features, int n_features) {
#ifdef HAS_ONNXRUNTIME
        auto memory_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
        std::array<int64_t, 2> input_shape = {1, n_features};
        auto input_tensor = Ort::Value::CreateTensor<float>(
            memory_info, const_cast<float*>(features.data()),
            features.size(), input_shape.data(), input_shape.size());

        const char* input_names[] = {"X"};
        const char* output_names[] = {"Y"};

        auto output = session_->Run(Ort::RunOptions{nullptr},
            input_names, &input_tensor, 1, output_names, 1);

        float* data = output[0].GetTensorMutableData<float>();
        auto shape = output[0].GetTensorTypeAndShapeInfo().GetShape();
        size_t n = 1;
        for (auto s : shape) n *= s;
        return std::vector<float>(data, data + n);
#else
        (void)features;
        (void)n_features;
        return {0.5f};
#endif
    }

private:
#ifdef HAS_ONNXRUNTIME
    std::unique_ptr<Ort::Env> env_;
    std::unique_ptr<Ort::Session> session_;
#endif
};

} // namespace hydra
